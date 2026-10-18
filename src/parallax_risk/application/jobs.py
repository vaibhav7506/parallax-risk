"""Durable job/object ports and validated state envelopes; resource ownership is explicit."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from parallax_risk.application.workflows import Operation
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import Identifier
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain.governance.contracts import Document


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    owner: str
    operation: Operation
    request: Document
    model_id: str
    version_id: str
    correlation_id: str
    status: JobStatus
    created: datetime
    updated: datetime
    result: Document | None
    error_code: str | None
    claim: str | None

    def __post_init__(self) -> None:
        for token in (self.job_id, self.owner, self.model_id, self.version_id, self.correlation_id):
            Identifier(token)
        utc_timestamp(self.created)
        utc_timestamp(self.updated)
        if (
            not isinstance(self.operation, Operation)
            or not isinstance(self.status, JobStatus)
            or not isinstance(self.request, Document)
            or self.updated < self.created
        ):
            raise DomainValidationError("Invalid job metadata")
        if self.claim is not None:
            Identifier(self.claim)
        if self.error_code is not None:
            Identifier(self.error_code)
        if (
            (self.status == JobStatus.SUCCEEDED) != (self.result is not None)
            or (self.status == JobStatus.FAILED) != (self.error_code is not None)
            or (self.status in (JobStatus.RUNNING, JobStatus.SUCCEEDED) and self.claim is None)
            or (self.status == JobStatus.QUEUED and self.claim is not None)
            or (self.result is not None and not isinstance(self.result, Document))
        ):
            raise DomainValidationError("Invalid job state envelope")


@dataclass(frozen=True, slots=True)
class StoredObject:
    owner: str
    kind: str
    key: str
    document: Document
    created: datetime

    def __post_init__(self) -> None:
        for token in (self.owner, self.kind, self.key):
            Identifier(token)
        utc_timestamp(self.created)
        if not isinstance(self.document, Document):
            raise DomainValidationError("Object requires immutable evidence")


@dataclass(frozen=True, slots=True)
class JobBrief:
    job_id: str
    operation: Operation
    status: JobStatus
    created: datetime
    updated: datetime
    error_code: str | None


@dataclass(frozen=True, slots=True)
class ObjectBrief:
    kind: str
    key: str
    content_hash: str
    created: datetime


class JobRepository(Protocol):
    def submit(self, job: Job, idempotency_key: str, maximum_pending: int) -> Job: ...
    def claim_next(self, token: str, now: datetime) -> Job | None: ...
    def finish(
        self, job: Job, result: Document | None, error_code: str | None, now: datetime
    ) -> None: ...
    def get(self, owner: str, job_id: str) -> Job | None: ...
    def list(self, owner: str, after: str, limit: int) -> tuple[JobBrief, ...]: ...
    def abandon(self, owner: str, job_id: str, now: datetime) -> None: ...
    def ready(self) -> None: ...


class ObjectRepository(Protocol):
    def put(self, item: StoredObject) -> StoredObject: ...
    def get(self, owner: str, kind: str, key: str) -> StoredObject | None: ...
    def list(self, owner: str, kind: str, after: str, limit: int) -> tuple[ObjectBrief, ...]: ...


class BackgroundExecutor(Protocol):
    """Local/distributed execution boundary; implementations own their worker lifetimes."""

    def start(self) -> None: ...
    def close(self) -> None: ...
