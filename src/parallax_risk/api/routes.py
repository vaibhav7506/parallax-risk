"""Thin versioned routers: authentication, transport envelopes and injected workflows."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Header, Query, Request, Response, Security
from fastapi.security import APIKeyHeader
from starlette.concurrency import run_in_threadpool

from parallax_risk.api.service_schemas import (
    DataResponse,
    GovernanceInput,
    JobInput,
    ObjectInput,
    ReportInput,
)
from parallax_risk.application.access import Principal, Role, ServiceError
from parallax_risk.application.service import RiskService
from parallax_risk.application.wire import value
from parallax_risk.application.workflows import COMMANDS, Operation
from parallax_risk.common.canonical import JsonValue

RESOURCE_PATHS = {
    "market/snapshots": "market",
    "portfolios": "portfolio",
    "counterparties": "counterparty",
    "netting-sets": "netting",
    "csas": "csa",
    "market/scenarios": "scenario",
    "market/pricing-contexts": "pricing-context",
}


def make_router(service: Callable[[], RiskService]) -> APIRouter:
    router = APIRouter(prefix="/v1")
    scheme = APIKeyHeader(
        name="X-API-Key",
        auto_error=False,
        description=(
            "Opaque credential; configure only its SHA-256 digest. Use TLS for remote access."
        ),
    )

    def principal(
        request: Request, credential: Annotated[str | None, Security(scheme)]
    ) -> Principal:
        return cast(Principal, request.state.principal)

    who = Annotated[Principal, Security(principal)]

    async def invoke(method: Callable[..., Any], *args: Any, **kwargs: Any) -> DataResponse:
        computed = await run_in_threadpool(method, *args, **kwargs)
        return DataResponse(data=value(computed))

    @router.get("/me", response_model=DataResponse, tags=["access"])
    def me(actor: who) -> DataResponse:
        return DataResponse(
            data={
                "subject": actor.subject,
                "roles": value(tuple(sorted(r.value for r in actor.roles))),
            }
        )

    @router.get("/workflows", response_model=DataResponse, tags=["workflows"])
    def workflows(actor: who) -> DataResponse:
        actor.require(Role.READER)
        from parallax_risk.application.wire_schema import schema

        return DataResponse(data={op.value: schema(cls) for op, cls in COMMANDS.items()})

    def resource(path: str, kind: str) -> None:
        async def ingest(body: ObjectInput, actor: who) -> DataResponse:
            return await invoke(
                service().ingest,
                actor,
                kind,
                body.key,
                cast(JsonValue, body.data),
                datetime.now(UTC),
            )

        async def read(key: str, actor: who) -> DataResponse:
            item = await run_in_threadpool(service().get_object, actor, kind, key)
            return DataResponse(
                data={"key": item.key, "hash": item.document.hash, "value": item.document.value()}
            )

        async def listing(
            actor: who, after: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
        ) -> DataResponse:
            return await invoke(service().object_page, actor, kind, after, limit)

        router.add_api_route(
            "/" + path,
            ingest,
            methods=["POST"],
            response_model=DataResponse,
            status_code=201,
            tags=[kind],
            name="ingest_" + kind,
        )
        router.add_api_route(
            "/" + path,
            listing,
            methods=["GET"],
            response_model=DataResponse,
            tags=[kind],
            name="list_" + kind,
        )
        router.add_api_route(
            "/" + path + "/{key}",
            read,
            methods=["GET"],
            response_model=DataResponse,
            tags=[kind],
            name="read_" + kind,
        )

    for path, kind in RESOURCE_PATHS.items():
        resource(path, kind)

    @router.get("/portfolios/{key}/{projection}", response_model=DataResponse, tags=["portfolio"])
    async def portfolio_parts(key: str, projection: str, actor: who) -> DataResponse:
        return await invoke(service().portfolio_parts, actor, key, projection)

    def calculation(operation: Operation) -> None:
        async def submit(
            body: JobInput,
            request: Request,
            actor: who,
            idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
        ) -> DataResponse:
            job = await run_in_threadpool(
                service().submit,
                actor,
                operation,
                cast(JsonValue, body.payload),
                model_id=body.model_id,
                version_id=body.version_id,
                is_synthetic=body.is_synthetic,
                idempotency_key=idempotency_key,
                correlation_id=request.state.correlation_id,
                now=datetime.now(UTC),
                calibration_job=body.calibration_job,
            )
            return DataResponse(
                data={
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "operation": job.operation.value,
                    "status_url": "/v1/runs/" + job.job_id,
                }
            )

        router.add_api_route(
            "/" + operation.value,
            submit,
            methods=["POST"],
            response_model=DataResponse,
            status_code=202,
            tags=[operation.value.split("/")[0]],
            name=operation.name.lower(),
            description=(
                "Schema-1 immutable command; obtain its exact JSON schema from GET "
                "/v1/workflows. Requires registered inputs/model/version and an "
                "Idempotency-Key. Result, input and lineage are retained under the "
                "returned run ID."
            ),
        )

    for operation in Operation:
        calculation(operation)

    @router.get("/runs", response_model=DataResponse, tags=["runs"])
    async def runs(
        actor: who, after: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
    ) -> DataResponse:
        return await invoke(service().job_page, actor, after, limit)

    @router.get("/runs/{key}", response_model=DataResponse, tags=["runs"])
    async def run(key: str, actor: who) -> DataResponse:
        job = await run_in_threadpool(service().job, actor, key)
        return DataResponse(
            data={
                "job_id": job.job_id,
                "operation": job.operation.value,
                "status": job.status.value,
                "created": job.created.isoformat(),
                "updated": job.updated.isoformat(),
                "error_code": job.error_code,
                "result_hash": None if job.result is None else job.result.hash,
            }
        )

    @router.get("/runs/{key}/input", response_model=DataResponse, tags=["runs"])
    async def input_data(key: str, actor: who) -> DataResponse:
        job = await run_in_threadpool(service().job, actor, key)
        return DataResponse(
            data={
                "model_id": job.model_id,
                "version_id": job.version_id,
                "operation": job.operation.value,
                "request": job.request.value(),
                "request_hash": job.request.hash,
            }
        )

    @router.get("/runs/{key}/result", response_model=DataResponse, tags=["runs"])
    async def result(key: str, actor: who) -> DataResponse:
        job = await run_in_threadpool(service().job, actor, key)
        if job.result is None:
            raise ServiceError(409, "job_has_no_successful_result")
        return DataResponse(
            data={"result": job.result.value(), "hash": job.result.hash, "lineage_id": job.job_id}
        )

    @router.post(
        "/runs/{key}/abandon",
        response_model=DataResponse,
        tags=["runs"],
        description=(
            "Operator marks a pending job failed; does not interrupt already "
            "executing numerical code. Never automatically requeue uncertain "
            "runs."
        ),
    )
    async def abandon(key: str, actor: who) -> DataResponse:
        await run_in_threadpool(service().abandon, actor, key, datetime.now(UTC))
        return DataResponse(data={"status": "failed"})

    @router.post("/governance", response_model=DataResponse, tags=["governance"])
    async def governance(body: GovernanceInput, actor: who) -> DataResponse:
        return await invoke(
            service().governance_write,
            actor,
            body.document,
            body.expected_revision,
            body.reason,
            datetime.now(UTC),
        )

    @router.get("/governance/{kind}/{key}", response_model=DataResponse, tags=["governance"])
    async def governance_get(kind: str, key: str, actor: who) -> DataResponse:
        return await invoke(service().governance_get, actor, kind, key)

    @router.get("/governance/{kind}", response_model=DataResponse, tags=["governance"])
    async def governance_list(
        kind: str, actor: who, after: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
    ) -> DataResponse:
        return await invoke(service().governance_page, actor, kind, after, limit)

    @router.post("/reports", response_model=DataResponse, status_code=201, tags=["reports"])
    async def report(body: ReportInput, actor: who) -> DataResponse:
        return await invoke(
            service().create_report,
            actor,
            body.kind,
            body.key,
            body.source_job,
            body.governance_keys,
            body.interpretation,
            datetime.now(UTC),
            body.governance_synthetic,
        )

    @router.get("/reports", response_model=DataResponse, tags=["reports"])
    async def reports(
        actor: who, after: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
    ) -> DataResponse:
        return await invoke(service().object_page, actor, "report", after, limit)

    @router.get("/reports/{key}", response_model=DataResponse, tags=["reports"])
    async def report_json(key: str, actor: who) -> DataResponse:
        item = await run_in_threadpool(service().get_object, actor, "report", key)
        return DataResponse(data=json_value(item.document.value()["json"]))

    @router.get("/reports/{key}/html", response_class=Response, tags=["reports"])
    async def report_html(key: str, actor: who) -> Response:
        item = await run_in_threadpool(service().get_object, actor, "report", key)
        return Response(
            content=cast(str, item.document.value()["html"]),
            media_type="text/html",
            headers={
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
                    "frame-ancestors 'none'"
                )
            },
        )

    return router


def json_value(text: JsonValue) -> JsonValue:
    from parallax_risk.application.wire import parse

    if not isinstance(text, str):
        raise ServiceError(500, "stored_report_invalid")
    return parse(text)
