"""PostgreSQL durable service records; explicit borrowed engine, no import-time IO."""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String, Table, Text, func, insert, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from parallax_risk.application.access import ServiceError
from parallax_risk.application.governance import ConflictError
from parallax_risk.application.jobs import Job, JobBrief, JobStatus, ObjectBrief, StoredObject
from parallax_risk.application.workflows import Operation
from parallax_risk.common.errors import InfrastructureError
from parallax_risk.domain.governance.contracts import Document
from parallax_risk.infrastructure.persistence.governance import metadata

objects = Table(
    "service_objects",
    metadata,
    Column("owner", String(128), primary_key=True),
    Column("kind", String(32), primary_key=True),
    Column("key", String(128), primary_key=True),
    Column("document", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("created", DateTime(timezone=True), nullable=False),
)
jobs = Table(
    "service_jobs",
    metadata,
    Column("job_id", String(128), primary_key=True),
    Column("owner", String(128), nullable=False),
    Column("operation", String(64), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
    Column("request", Text, nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("model_id", String(128), nullable=False),
    Column("version_id", String(128), nullable=False),
    Column("correlation_id", String(128), nullable=False),
    Column("status", String(16), nullable=False),
    Column("created", DateTime(timezone=True), nullable=False),
    Column("updated", DateTime(timezone=True), nullable=False),
    Column("result", Text),
    Column("result_hash", String(64)),
    Column("error_code", String(64)),
    Column("claim", String(128)),
    Column("lineage_kind", String(32), nullable=False),
    Column("lineage_key", String(128)),
)


def _document(payload: str, digest: str) -> Document:
    try:
        result = Document(payload)
        if result.hash == digest:
            return result
    except Exception:
        pass
    raise InfrastructureError("Service evidence integrity check failed")


def _job(row: Any) -> Job:
    return Job(
        row.job_id,
        row.owner,
        Operation(row.operation),
        _document(row.request, row.request_hash),
        row.model_id,
        row.version_id,
        row.correlation_id,
        JobStatus(row.status),
        row.created,
        row.updated,
        None if row.result is None else _document(row.result, row.result_hash),
        row.error_code,
        row.claim,
    )


class PostgresObjects:
    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise InfrastructureError("Service records require PostgreSQL")
        self.engine = engine

    def put(self, item: StoredObject) -> StoredObject:
        try:
            with self.engine.begin() as connection:
                # Serialize this namespace/key, so equal duplicate submissions converge.
                lock = item.owner + ":" + item.kind + ":" + item.key
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 12))"), {"key": lock}
                )
                row = connection.execute(
                    select(objects).where(
                        objects.c.owner == item.owner,
                        objects.c.kind == item.kind,
                        objects.c.key == item.key,
                    )
                ).first()
                if row is not None:
                    old = self._object(row)
                    if old.document.hash != item.document.hash:
                        raise ConflictError("Immutable object identifier collision")
                    return old
                connection.execute(
                    insert(objects).values(
                        owner=item.owner,
                        kind=item.kind,
                        key=item.key,
                        document=item.document.text,
                        content_hash=item.document.hash,
                        created=item.created,
                    )
                )
            return item
        except SQLAlchemyError:
            raise InfrastructureError("Service object persistence failed") from None

    @staticmethod
    def _object(row: Any) -> StoredObject:
        return StoredObject(
            row.owner, row.kind, row.key, _document(row.document, row.content_hash), row.created
        )

    def get(self, owner: str, kind: str, key: str) -> StoredObject | None:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    select(objects).where(
                        objects.c.owner == owner, objects.c.kind == kind, objects.c.key == key
                    )
                ).first()
            return None if row is None else self._object(row)
        except SQLAlchemyError:
            raise InfrastructureError("Service object lookup failed") from None

    def list(self, owner: str, kind: str, after: str, limit: int) -> tuple[ObjectBrief, ...]:
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(objects.c.kind, objects.c.key, objects.c.content_hash, objects.c.created)
                    .where(objects.c.owner == owner, objects.c.kind == kind, objects.c.key > after)
                    .order_by(objects.c.key)
                    .limit(limit)
                ).all()
            return tuple(ObjectBrief(r.kind, r.key, r.content_hash, r.created) for r in rows)
        except SQLAlchemyError:
            raise InfrastructureError("Service object listing failed") from None


class PostgresJobs:
    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise InfrastructureError("Service jobs require PostgreSQL")
        self.engine = engine

    def ready(self) -> None:
        try:
            with self.engine.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                if revision != "0012":
                    raise InfrastructureError("Service schema is not revision 0012")
                connection.execute(select(jobs.c.job_id).limit(0))
        except SQLAlchemyError:
            raise InfrastructureError("Service schema unavailable") from None

    def submit(self, job: Job, idempotency_key: str, maximum_pending: int) -> Job:
        try:
            with self.engine.begin() as connection:
                # Global admission lock prevents concurrent submissions bypassing the cap.
                connection.execute(text("SELECT pg_advisory_xact_lock(120012)"))
                row = connection.execute(
                    select(jobs).where(
                        jobs.c.owner == job.owner, jobs.c.idempotency_key == idempotency_key
                    )
                ).first()
                if row is not None:
                    old = _job(row)
                    if (old.operation, old.request.hash, old.model_id, old.version_id) != (
                        job.operation,
                        job.request.hash,
                        job.model_id,
                        job.version_id,
                    ):
                        raise ConflictError("Idempotency key reused for different input")
                    return old
                pending = connection.execute(
                    select(func.count())
                    .select_from(jobs)
                    .where(jobs.c.status.in_(("queued", "running")))
                ).scalar_one()
                if pending >= maximum_pending:
                    raise ServiceError(429, "job_capacity_exhausted")
                connection.execute(
                    insert(jobs).values(
                        job_id=job.job_id,
                        owner=job.owner,
                        operation=job.operation.value,
                        idempotency_key=idempotency_key,
                        request=job.request.text,
                        request_hash=job.request.hash,
                        model_id=job.model_id,
                        version_id=job.version_id,
                        correlation_id=job.correlation_id,
                        status="queued",
                        created=job.created,
                        updated=job.updated,
                        lineage_kind="lineage",
                    )
                )
            return job
        except IntegrityError:
            raise ConflictError("Job identity collision") from None
        except SQLAlchemyError:
            raise InfrastructureError("Job submission failed") from None

    def claim_next(self, token: str, now: datetime) -> Job | None:
        try:
            with self.engine.begin() as connection:
                row = connection.execute(
                    select(jobs)
                    .where(jobs.c.status == "queued")
                    .order_by(jobs.c.created, jobs.c.job_id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                ).first()
                if row is None:
                    return None
                updated = connection.execute(
                    update(jobs)
                    .where(jobs.c.job_id == row.job_id)
                    .values(status="running", claim=token, updated=now)
                    .returning(jobs)
                ).one()
                return _job(updated)
        except SQLAlchemyError:
            raise InfrastructureError("Job claim failed") from None

    def finish(
        self, job: Job, result: Document | None, error_code: str | None, now: datetime
    ) -> None:
        if (
            job.status != JobStatus.RUNNING
            or job.claim is None
            or (result is None) == (error_code is None)
        ):
            raise ConflictError("Invalid job completion")
        try:
            with self.engine.begin() as connection:
                rows = connection.execute(
                    update(jobs)
                    .where(
                        jobs.c.job_id == job.job_id,
                        jobs.c.status == "running",
                        jobs.c.claim == job.claim,
                    )
                    .values(
                        status="succeeded" if result is not None else "failed",
                        result=None if result is None else result.text,
                        result_hash=None if result is None else result.hash,
                        error_code=error_code,
                        lineage_key=job.job_id if result is not None else None,
                        updated=now,
                    )
                    .returning(jobs.c.job_id)
                ).all()
                if len(rows) != 1:
                    raise ConflictError("Stale job claim")
        except IntegrityError:
            raise ConflictError("Job completion requires committed lineage") from None
        except SQLAlchemyError:
            raise InfrastructureError("Job completion failed") from None

    def get(self, owner: str, job_id: str) -> Job | None:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    select(jobs).where(jobs.c.owner == owner, jobs.c.job_id == job_id)
                ).first()
            return None if row is None else _job(row)
        except SQLAlchemyError:
            raise InfrastructureError("Job lookup failed") from None

    def list(self, owner: str, after: str, limit: int) -> tuple[JobBrief, ...]:
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(
                        jobs.c.job_id,
                        jobs.c.operation,
                        jobs.c.status,
                        jobs.c.created,
                        jobs.c.updated,
                        jobs.c.error_code,
                    )
                    .where(jobs.c.owner == owner, jobs.c.job_id > after)
                    .order_by(jobs.c.job_id)
                    .limit(limit)
                ).all()
            return tuple(
                JobBrief(
                    r.job_id,
                    Operation(r.operation),
                    JobStatus(r.status),
                    r.created,
                    r.updated,
                    r.error_code,
                )
                for r in rows
            )
        except SQLAlchemyError:
            raise InfrastructureError("Job listing failed") from None

    def abandon(self, owner: str, job_id: str, now: datetime) -> None:
        try:
            with self.engine.begin() as connection:
                rows = connection.execute(
                    update(jobs)
                    .where(
                        jobs.c.owner == owner,
                        jobs.c.job_id == job_id,
                        jobs.c.status.in_(("queued", "running")),
                    )
                    .values(status="failed", error_code="operator_abandoned", updated=now)
                    .returning(jobs.c.job_id)
                ).all()
                if not rows:
                    raise ConflictError("Only pending jobs can be abandoned")
        except SQLAlchemyError:
            raise InfrastructureError("Job abandonment failed") from None
