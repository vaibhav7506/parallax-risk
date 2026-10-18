"""Executor error states stop uncertain persistence and never replay a claim."""

import io
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from parallax_risk.application.jobs import Job, JobStatus, StoredObject
from parallax_risk.application.workflows import Operation
from parallax_risk.common.errors import (
    ConfigurationError,
    DomainValidationError,
    InfrastructureError,
)
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.governance.contracts import Document
from parallax_risk.infrastructure.worker import ThreadExecutor


def job():
    now = datetime.now(UTC)
    return Job(
        "job",
        "owner",
        Operation.CURVE,
        Document.of({"payload": {}}),
        "model",
        "version",
        "correlation",
        JobStatus.RUNNING,
        now,
        now,
        None,
        None,
        "claim",
    )


@pytest.mark.parametrize(
    "error,finish,events",
    [
        (None, True, "job_completed"),
        (DomainValidationError("SECRET"), True, "calculation_rejected"),
        (ValueError("SECRET"), True, "calculation_failed"),
        (InfrastructureError("SECRET"), False, "worker_persistence_uncertain"),
    ],
)
def test_claim_compute_and_sanitized_failure_states(error, finish, events):
    log = io.StringIO()
    calls = []
    result = Document.of({"actual": 1})

    def compute(*args):
        if error:
            raise error
        return result

    def complete(*args):
        calls.append(args)
        worker.stop.set()

    service = SimpleNamespace(
        jobs=SimpleNamespace(claim_next=lambda *_: job(), finish=complete), compute=compute
    )
    worker = ThreadExecutor(service, create_logger(stream=log))
    worker._loop("claim")
    assert bool(calls) == finish and events in log.getvalue() and "SECRET" not in log.getvalue()
    if calls:
        assert calls[0][1] == (result if error is None else None)
        assert calls[0][2] == (
            None
            if error is None
            else "calculation_rejected"
            if isinstance(error, DomainValidationError)
            else "internal_calculation_failure"
        )


@pytest.mark.parametrize("boundary", ["claim", "finish"])
def test_database_uncertainty_halts_worker_without_retry(boundary):
    log = io.StringIO()
    count = []

    def broken(*args):
        count.append(boundary)
        raise InfrastructureError("SECRET database")

    service = SimpleNamespace(
        jobs=SimpleNamespace(
            claim_next=broken if boundary == "claim" else lambda *_: job(), finish=broken
        ),
        compute=lambda *_: Document.of({"actual": 1}),
    )
    worker = ThreadExecutor(service, create_logger(stream=log))
    worker._loop("claim")
    assert count == [boundary] and "halted" in log.getvalue() and "SECRET" not in log.getvalue()


def test_worker_lifecycle_idle_close_and_invalid_parallel_counts():
    for count in (True, 0, 5):
        with pytest.raises(ConfigurationError):
            ThreadExecutor(None, create_logger(stream=io.StringIO()), count)
    calls = []
    service = SimpleNamespace(
        jobs=SimpleNamespace(ready=lambda: calls.append("ready"), claim_next=lambda *_: None)
    )
    worker = ThreadExecutor(service, create_logger(stream=io.StringIO()), 2)
    assert not worker.healthy
    worker.start()
    assert worker.healthy and calls == ["ready"]
    with pytest.raises(ConfigurationError):
        worker.start()
    worker.close()
    assert not worker.healthy
    with pytest.raises(ConfigurationError):
        worker.start()


@pytest.mark.parametrize(
    "changes",
    [
        {"status": JobStatus.QUEUED},
        {"status": JobStatus.SUCCEEDED},
        {"status": JobStatus.FAILED},
        {"error_code": "bad"},
        {"result": Document.of({})},
        {"claim": None},
        {"status": "running"},
        {"operation": "simulation"},
        {"request": {}},
    ],
)
def test_invalid_job_state_envelopes_rejected_before_persistence(changes):
    with pytest.raises(DomainValidationError):
        replace(job(), **changes)


def test_stored_object_requires_immutable_document():
    with pytest.raises(DomainValidationError):
        StoredObject("owner", "kind", "key", {}, datetime.now(UTC))
