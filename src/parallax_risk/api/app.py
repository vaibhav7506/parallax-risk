"""Factory-based FastAPI composition; imports never start engines or load settings."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from parallax_risk import __version__
from parallax_risk.api.guard import RequestGuard, problem
from parallax_risk.api.routes import make_router
from parallax_risk.api.schemas import HealthResponse, ReadinessResponse, VersionResponse
from parallax_risk.application.access import Authenticator, ServiceError
from parallax_risk.application.config import Settings, load_settings
from parallax_risk.application.governance import ConflictError
from parallax_risk.application.ports import ConnectivityProbe
from parallax_risk.application.service import RiskService
from parallax_risk.application.service_config import ServiceSettings, load_service_settings
from parallax_risk.common.errors import (
    ConfigurationError,
    DomainValidationError,
    InfrastructureError,
    ParallaxError,
)
from parallax_risk.common.logging import create_logger
from parallax_risk.infrastructure.authentication import DigestAuthenticator
from parallax_risk.infrastructure.persistence.database import PostgresConnectivity
from parallax_risk.infrastructure.service_composition import make_service
from parallax_risk.infrastructure.worker import ThreadExecutor


def create_app(
    settings: Settings | None = None,
    *,
    connectivity: ConnectivityProbe | None = None,
    service_settings: ServiceSettings | None = None,
    authenticator: Authenticator | None = None,
    service: RiskService | None = None,
    executor: ThreadExecutor | None = None,
) -> FastAPI:
    """Compose operational endpoints and own dependency cleanup in lifespan.

    An injected probe is application-owned and is closed at shutdown.
    Database failures degrade /ready to 503; /health stays a liveness probe.
    """
    effective = load_settings() if settings is None else settings
    service_config = load_service_settings() if service_settings is None else service_settings
    auth = DigestAuthenticator(service_config.entries()) if authenticator is None else authenticator
    if (
        effective.environment == "production"
        and service_config.credentials is None
        and authenticator is None
    ):
        raise ConfigurationError("Production requires explicit service authentication")
    if (
        service_config.credentials is not None
        and effective.database_url is None
        and service is None
    ):
        raise ConfigurationError("Authenticated service requires explicit PostgreSQL")
    logger = create_logger(effective.log_level)
    probe = connectivity
    started = False
    runtime = service
    worker = executor
    engine: Engine | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal probe, started, runtime, worker, engine
        try:
            if probe is None and effective.database_url is not None:
                probe = PostgresConnectivity(
                    effective.database_url.get_secret_value(),
                    timeout_seconds=effective.database_connect_timeout_seconds,
                )
            if (
                runtime is None
                and service_config.credentials is not None
                and effective.database_url is not None
            ):
                engine = create_engine(
                    effective.database_url.get_secret_value(),
                    hide_parameters=True,
                    connect_args={
                        "connect_timeout": effective.database_connect_timeout_seconds,
                        "options": "-c statement_timeout=30000 -c lock_timeout=10000",
                    },
                )
                runtime = make_service(engine, logger, service_config.maximum_pending_jobs)
                worker = ThreadExecutor(runtime, logger, service_config.workers)
            if runtime is not None:
                await run_in_threadpool(runtime.jobs.ready)
            if worker is not None:
                await run_in_threadpool(worker.start)
            started = True
            logger.event("service_started", outcome=effective.environment)
            yield
        finally:
            started = False
            try:
                if worker is not None:
                    await run_in_threadpool(worker.close)
            finally:
                if engine is not None:
                    await run_in_threadpool(engine.dispose)
                    runtime, worker, engine = service, executor, None
                if probe is not None:
                    await run_in_threadpool(probe.close)
            logger.event("service_stopped", outcome="closed")

    app = FastAPI(title="Parallax Risk", version=__version__, lifespan=lifespan)
    app.add_middleware(RequestGuard, authenticator=auth, settings=service_config, logger=logger)
    if service_config.origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(service_config.origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["X-API-Key", "X-Request-ID", "Idempotency-Key", "Content-Type"],
            expose_headers=["X-Request-ID"],
        )

    def get_service() -> RiskService:
        if not started or runtime is None:
            raise ServiceError(503, "financial_service_not_configured")
        return runtime

    app.include_router(make_router(get_service))

    async def failure(request: Request, error: Exception) -> Response:
        correlation = getattr(request.state, "correlation_id", "unknown")
        if isinstance(error, ServiceError):
            status, code = error.status, error.code
        elif isinstance(error, ConflictError):
            status, code = 409, "revision_or_identity_conflict"
        elif isinstance(error, (DomainValidationError, RequestValidationError)):
            status, code = 422, "invalid_workflow_input"
        elif isinstance(error, InfrastructureError):
            status, code = 503, "dependency_unavailable"
        elif isinstance(error, HTTPException):
            status, code = error.status_code, "http_request_rejected"
        elif isinstance(error, ParallaxError):
            status, code = 422, "calculation_rejected"
        else:
            status, code = 500, "internal_service_failure"
        logger.event(
            "http_failure", run_id=correlation, outcome=code, error_type=type(error).__name__
        )
        return Response(
            problem(status, code, correlation),
            status_code=status,
            media_type="application/problem+json",
            headers={
                "X-Request-ID": correlation,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    for exception in (ParallaxError, RequestValidationError, HTTPException, Exception):
        app.add_exception_handler(exception, failure)

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/ready", response_model=ReadinessResponse, tags=["operations"])
    async def ready(response: Response) -> ReadinessResponse:
        if not started:
            response.status_code = 503
            return ReadinessResponse(status="not_ready", database="unavailable")
        if probe is None:
            response.status_code = 503
            return ReadinessResponse(status="not_ready", database="not_configured")
        try:
            await run_in_threadpool(probe.check)
            if runtime is not None:
                await run_in_threadpool(runtime.jobs.ready)
            if worker is not None and not worker.healthy:
                raise InfrastructureError("Compute executor unavailable")
        except InfrastructureError:
            response.status_code = 503
            logger.event(
                "dependency_check", outcome="unavailable", error_type="InfrastructureError"
            )
            return ReadinessResponse(status="not_ready", database="unavailable")
        return ReadinessResponse(status="ready", database="connected")

    @app.get("/version", response_model=VersionResponse, tags=["operations"])
    def version() -> VersionResponse:
        return VersionResponse(version=__version__)

    return app
