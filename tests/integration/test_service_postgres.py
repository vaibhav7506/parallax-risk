"""Actual PostgreSQL 0012, service transactions, jobs and authenticated financial API."""

import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from parallax_risk.api.app import create_app
from parallax_risk.application.access import Principal, Role, ServiceError
from parallax_risk.application.config import Settings
from parallax_risk.application.governance import ConflictError
from parallax_risk.application.governance_codec import encode
from parallax_risk.application.jobs import JobStatus, StoredObject
from parallax_risk.application.service_config import ServiceSettings
from parallax_risk.application.service_demo import demonstrate
from parallax_risk.application.service_examples import commands
from parallax_risk.application.wire import value
from parallax_risk.application.workflows import Operation
from parallax_risk.common.errors import DomainValidationError, InfrastructureError
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.governance.contracts import Document
from parallax_risk.infrastructure.authentication import DigestAuthenticator
from parallax_risk.infrastructure.persistence.migrate import migrate
from parallax_risk.infrastructure.persistence.service import _document
from parallax_risk.infrastructure.service_composition import make_service
from parallax_risk.infrastructure.worker import ThreadExecutor
from tests.api.test_operations import Probe
from tests.integration.test_governance_postgres import database as database_11  # noqa: F401
from tests.unit.test_governance import MODEL, VERSION

pytestmark = pytest.mark.postgres
ACTOR = Principal("researcher", frozenset(Role))
OTHER = Principal("other", frozenset(Role))
TOKEN = "synthetic-verification-token-" + "a" * 32


@pytest.fixture
def database(database_11):  # noqa: F811
    with database_11.begin() as connection:
        migrate(connection)
    return database_11


@pytest.fixture
def service(database):
    service = make_service(database, create_logger(stream=io.StringIO()))
    now = datetime.now(UTC)
    service.governance.record(
        MODEL,
        expected_revision=0,
        actor=ACTOR.subject,
        timestamp=now,
        reason="Synthetic test inventory",
    )
    service.governance.record(
        replace(VERSION, created=now - timedelta(seconds=1)),
        expected_revision=0,
        actor=ACTOR.subject,
        timestamp=now,
        reason="Synthetic test version",
    )
    return service


def submission(service, key="first", owner=ACTOR, operation=Operation.CURVE, command=None):
    return service.submit(
        owner,
        operation,
        value(command or commands(2)[operation]),
        model_id="model",
        version_id="version",
        is_synthetic=True,
        idempotency_key=key,
        correlation_id=uuid4().hex,
        now=datetime.now(UTC),
    )


def test_migrate_0011_to_0012_repeat_then_explicit_zero_reupgrade(database):
    assert {"service_jobs", "service_objects", "governance_heads", "governance_events"} <= set(
        inspect(database).get_table_names()
    )
    with database.begin() as connection:
        migrate(connection)
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0012"
        )
        migrate(connection, downgrade_to_base=True, allow_destructive=True)
        migrate(connection)
    assert "service_jobs" in inspect(database).get_table_names()


def test_immutable_objects_owner_pagination_integrity_and_sql_protection(service, database):
    now = datetime.now(UTC)
    first = StoredObject(ACTOR.subject, "test", "a", Document.of({"data": 1}), now)
    assert service.objects.put(first) == first
    assert service.objects.put(replace(first, created=now + timedelta(seconds=1))) == first
    service.objects.put(replace(first, key="b"))
    assert service.objects.get(OTHER.subject, "test", "a") is None
    assert [x.key for x in service.objects.list(ACTOR.subject, "test", "a", 1)] == ["b"]
    with pytest.raises(ConflictError):
        service.objects.put(replace(first, document=Document.of({"data": 2})))
    for sql in ("UPDATE service_objects SET document='{}'", "DELETE FROM service_objects"):
        with pytest.raises(SQLAlchemyError), database.begin() as connection:
            connection.execute(text(sql))
    with pytest.raises(InfrastructureError):
        _document(first.document.text, "a" * 64)
    with pytest.raises(InfrastructureError):
        _document("invalid", "a" * 64)
    assert len(service.objects.list(ACTOR.subject, "test", "", 100)) == 2


def test_idempotency_claim_cas_success_requires_lineage_and_terminal_immutability(
    service, database
):
    original = submission(service)
    assert submission(service).job_id == original.job_id
    with pytest.raises(ConflictError):
        submission(service, operation=Operation.INVARIANTS)
    assert service.jobs.get(OTHER.subject, original.job_id) is None
    running = service.jobs.claim_next("claim", datetime.now(UTC))
    assert running.job_id == original.job_id and running.status == JobStatus.RUNNING
    assert service.jobs.claim_next("other-claim", datetime.now(UTC)) is None
    with pytest.raises(ConflictError):
        service.jobs.finish(
            running, Document.of({"value": "without lineage"}), None, datetime.now(UTC)
        )
    result = service.compute(running, datetime.now(UTC))
    service.jobs.finish(running, result, None, datetime.now(UTC))
    saved = service.jobs.get(ACTOR.subject, original.job_id)
    assert saved.status == JobStatus.SUCCEEDED and saved.result == result
    with pytest.raises(ConflictError):
        service.jobs.finish(running, result, None, datetime.now(UTC))
    with pytest.raises(ConflictError):
        service.jobs.abandon(ACTOR.subject, saved.job_id, datetime.now(UTC))
    for sql in (
        "UPDATE service_jobs SET request='{}'",
        "UPDATE service_jobs SET status='queued'",
        "UPDATE service_jobs SET result='{}'",
    ):
        with pytest.raises(SQLAlchemyError), database.begin() as connection:
            connection.execute(text(sql))


def test_concurrent_idempotency_admission_and_exclusive_claim(service):
    barrier = Barrier(4)

    def same(_):
        barrier.wait()
        return submission(service).job_id

    with ThreadPoolExecutor(4) as pool:
        ids = tuple(pool.map(same, range(4)))
    assert len(set(ids)) == 1
    job = service.jobs.get(ACTOR.subject, ids[0])
    with pytest.raises(ServiceError) as error:
        service.jobs.submit(replace(job, job_id=uuid4().hex), "another", 1)
    assert error.value.status == 429
    with ThreadPoolExecutor(4) as pool:
        claims = tuple(
            pool.map(
                lambda i: service.jobs.claim_next("claim" + str(i), datetime.now(UTC)), range(4)
            )
        )
    assert sum(x is not None for x in claims) == 1


def test_failure_abandonment_input_role_guards_and_registration(service):
    job = submission(service)
    with pytest.raises(ServiceError):
        service.abandon(
            Principal(ACTOR.subject, frozenset({Role.READER})), job.job_id, datetime.now(UTC)
        )
    service.abandon(ACTOR, job.job_id, datetime.now(UTC))
    assert service.jobs.get(ACTOR.subject, job.job_id).error_code == "operator_abandoned"
    with pytest.raises(ServiceError):
        service.job(OTHER, job.job_id)
    with pytest.raises(DomainValidationError):
        submission(service, key="unregistered", operation=Operation.XVA)
    with pytest.raises(ServiceError):
        service.ingest(
            Principal("reader", frozenset({Role.READER})), "market", "x", {}, datetime.now(UTC)
        )
    with pytest.raises(DomainValidationError):
        service.object_page(ACTOR, "market", "", True)
    queued = submission(service, "fail")
    running = service.jobs.claim_next("failed-claim", datetime.now(UTC))
    service.jobs.finish(running, None, "calculation_rejected", datetime.now(UTC))
    assert service.jobs.get(ACTOR.subject, queued.job_id).status == JobStatus.FAILED
    assert service.jobs.list(ACTOR.subject, "", 100)


def test_transaction_failure_rolls_back_and_sanitizes_secret(service, database):
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO service_jobs"):
            raise OperationalError("SECRET SQL", {}, Exception("SECRET CREDENTIAL"))

    event.listen(database, "before_cursor_execute", fail)
    try:
        with pytest.raises(InfrastructureError) as error:
            submission(service)
        assert "SECRET" not in str(error.value)
    finally:
        event.remove(database, "before_cursor_execute", fail)
    assert service.jobs.list(ACTOR.subject, "", 100) == ()
    assert submission(service).status == JobStatus.QUEUED


def test_full_authenticated_synthetic_demo_replay_reports_access_and_input_rejection(service):
    auth = DigestAuthenticator(
        (
            (hashlib.sha256(TOKEN.encode()).hexdigest(), ACTOR),
            (hashlib.sha256((TOKEN + "other").encode()).hexdigest(), OTHER),
            (
                hashlib.sha256((TOKEN + "reader").encode()).hexdigest(),
                Principal("reader", frozenset({Role.READER})),
            ),
        )
    )
    worker = ThreadExecutor(service, create_logger(stream=io.StringIO()), 2)
    app = create_app(
        Settings(),
        connectivity=Probe(),
        service_settings=ServiceSettings(requests_per_minute=10000),
        authenticator=auth,
        service=service,
        executor=worker,
    )
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:

        class Client:
            def request(self, method, path, payload=None, *, idempotency_key=None):
                headers = {} if idempotency_key is None else {"Idempotency-Key": idempotency_key}
                response = client.request(method, path, json=payload, headers=headers)
                assert response.is_success, response.text
                return response.json()

        result = demonstrate(Client(), ACTOR.subject, paths=2)
        assert len(result["jobs"]) == 16 and result["replay_equal"]
        assert result["weak_mutation_misses"] > 0
        assert len(result["report_ids"]) == 7
        for key in result["report_ids"]:
            assert client.get("/v1/reports/" + key).json()["data"]["report"]["is_synthetic"] is True
            html = client.get("/v1/reports/" + key + "/html")
            assert (
                html.status_code == 200
                and "default-src 'none'" in html.headers["content-security-policy"]
            )
            assert (
                client.get("/v1/reports/" + key, headers={"X-API-Key": TOKEN + "other"}).status_code
                == 404
            )
        assert client.get("/ready").status_code == 200
        assert len(client.get("/v1/workflows").json()["data"]) == 16
        assert client.get("/v1/me").json()["data"]["subject"] == ACTOR.subject
        assert client.get("/v1/runs?limit=2").status_code == 200
        assert client.get("/v1/governance/model?limit=2").status_code == 200
        assert client.get("/v1/portfolios/synthetic-phase12:1/csas").status_code in (200, 404)
        assert (
            client.post(
                "/v1/governance",
                json={"document": encode(MODEL).value(), "expected_revision": 0, "reason": "bad"},
                headers={"X-API-Key": TOKEN + "reader"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/v1/xva",
                json={
                    "payload": {},
                    "is_synthetic": True,
                    "model_id": "model",
                    "version_id": "version",
                },
                headers={"Idempotency-Key": "bad"},
            ).status_code
            == 422
        )
        assert client.get("/v1/runs/missing/result").status_code == 404
        assert client.get("/v1/runs?limit=101").status_code == 422
    assert not worker.healthy
