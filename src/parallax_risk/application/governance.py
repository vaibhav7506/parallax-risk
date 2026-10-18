"""Injected governance workflow; persistence commits each snapshot and audit event atomically."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from parallax_risk.application.governance_codec import StoredRecord, encode, record_key
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.governance.contracts import (
    Approval,
    Finding,
    FindingStatus,
    Lineage,
    Model,
    ModelStatus,
    Version,
    finding_transition,
    integer,
)
from parallax_risk.domain.governance.monitoring import Alert, AlertState, Evaluation


class ConflictError(DomainValidationError):
    """A stale revision or identifier collision; caller must reread."""


@dataclass(frozen=True, slots=True)
class Snapshot:
    record: StoredRecord
    revision: int
    actor: str
    timestamp: datetime
    reason: str

    def __post_init__(self) -> None:
        encode(self.record)
        integer(self.revision, 1)
        require_text(self.actor)
        require_text(self.reason)
        object.__setattr__(self, "timestamp", utc_timestamp(self.timestamp))


@dataclass(frozen=True, slots=True)
class Reference:
    kind: str
    entity_id: str
    revision: int

    def __post_init__(self) -> None:
        require_token(self.kind)
        require_token(self.entity_id)
        integer(self.revision, 1)

    @classmethod
    def of(cls, snapshot: Snapshot) -> "Reference":
        return cls(*record_key(snapshot.record), snapshot.revision)


class GovernanceRepository(Protocol):
    def get(self, kind: str, entity_id: str) -> Snapshot | None: ...

    def history(self, kind: str, entity_id: str) -> tuple[Snapshot, ...]: ...

    def list(self, kind: str, after: str, limit: int) -> tuple[Snapshot, ...]: ...

    def save(
        self, snapshot: Snapshot, expected_revision: int, references: tuple[Reference, ...]
    ) -> None:
        """CAS head + append audit event in one transaction; lock/check reference revisions."""
        ...


class Governance:
    """Research workflow with caller-supplied actors/time, not an authentication service.

    Decisions preserve explicit authority/evidence; they do not change model status,
    close findings, waive limitations or confer regulatory approval automatically.
    """

    def __init__(self, repository: GovernanceRepository) -> None:
        self.repository = repository

    def _get(self, kind: str, entity_id: str) -> Snapshot:
        value = self.repository.get(kind, entity_id)
        if value is None:
            raise DomainValidationError("Required governance record does not exist")
        return value

    def record(
        self,
        record: StoredRecord,
        *,
        expected_revision: int,
        actor: str,
        timestamp: datetime,
        reason: str,
    ) -> Snapshot:
        timestamp = utc_timestamp(timestamp)
        integer(expected_revision)
        kind, entity_id = record_key(record)
        previous = self.repository.get(kind, entity_id)
        actual = previous.revision if previous is not None else 0
        if actual != expected_revision:
            raise ConflictError("Governance revision changed")
        references: list[Reference] = []
        if not isinstance(record, Model):
            model = self._get("model", record.model_id)
            references.append(Reference.of(model))
            if not isinstance(record, Version):
                version = self._get("version", record.version_id)
                if (
                    not isinstance(version.record, Version)
                    or version.record.model_id != record.model_id
                ):
                    raise DomainValidationError("Version belongs to a different model")
                references.append(Reference.of(version))
        if previous is not None:
            if timestamp < previous.timestamp:
                raise DomainValidationError("Audit timestamps cannot move backwards")
            if isinstance(record, Finding) and isinstance(previous.record, Finding):
                finding_transition(previous.record, record)
            elif isinstance(record, Model) and isinstance(previous.record, Model):
                allowed = {
                    ModelStatus.DEVELOPMENT: ModelStatus.VALIDATION,
                    ModelStatus.VALIDATION: ModelStatus.ACTIVE,
                    ModelStatus.ACTIVE: ModelStatus.RETIRED,
                }
                if (
                    record.status != previous.record.status
                    and allowed.get(previous.record.status) != record.status
                ):
                    raise DomainValidationError("Invalid model status transition")
            elif isinstance(record, Alert) and isinstance(previous.record, Alert):
                before = previous.record
                if (
                    record.model_id,
                    record.version_id,
                    record.evaluation_id,
                    record.severity,
                    record.evidence,
                ) != (
                    before.model_id,
                    before.version_id,
                    before.evaluation_id,
                    before.severity,
                    before.evidence,
                ):
                    raise DomainValidationError("Alert opening evidence and scope are immutable")
                allowed_alerts = {
                    AlertState.OPEN: AlertState.ACKNOWLEDGED,
                    AlertState.ACKNOWLEDGED: AlertState.RESOLVED,
                }
                if allowed_alerts.get(before.state) != record.state:
                    raise DomainValidationError("Invalid alert state transition")
            else:
                raise ConflictError("This governance record is immutable")
        else:
            if isinstance(record, Model) and record.status != ModelStatus.DEVELOPMENT:
                raise DomainValidationError("New models must begin in development")
            if isinstance(record, Finding) and record.status != FindingStatus.OPEN:
                raise DomainValidationError("New findings must be open")
            if isinstance(record, Alert) and record.state != AlertState.OPEN:
                raise DomainValidationError("New alerts must be open")
        if isinstance(record, Approval) and record.decided > timestamp:
            raise DomainValidationError("Decision cannot postdate its audit event")
        if isinstance(record, Version) and record.created > timestamp:
            raise DomainValidationError("Version cannot postdate its audit event")
        if isinstance(record, Lineage) and record.timestamp > timestamp:
            raise DomainValidationError("Risk run cannot postdate its audit event")
        if isinstance(record, Model) and record.status == ModelStatus.ACTIVE:
            registered = self._get("version", record.version)
            if (
                not isinstance(registered.record, Version)
                or registered.record.model_id != record.model_id
            ):
                raise DomainValidationError("Active inventory version must belong to this model")
            references.append(Reference.of(registered))
        if isinstance(record, Evaluation):
            policy = self._get("policy", record.policy.policy_id)
            if policy.record != record.policy:
                raise DomainValidationError("Evaluation must use the registered immutable policy")
            if record.current.timestamp > timestamp:
                raise DomainValidationError("Observation cannot postdate its audit event")
            references.append(Reference.of(policy))
        if isinstance(record, Alert):
            opening = self._get("evaluation", record.evaluation_id)
            evaluation = opening.record
            if (
                not isinstance(evaluation, Evaluation)
                or not evaluation.triggered
                or (evaluation.model_id, evaluation.version_id, evaluation.policy.severity)
                != (record.model_id, record.version_id, record.severity)
            ):
                raise DomainValidationError(
                    "Alert requires a breached evaluation with matching scope/severity"
                )
            references.append(Reference.of(opening))
            if record.state == AlertState.RESOLVED:
                if record.resolution_evaluation_id is None:
                    raise DomainValidationError("Recovery evaluation is required")
                recovery = self._get("evaluation", record.resolution_evaluation_id)
                recovered = recovery.record
                if (
                    not isinstance(recovered, Evaluation)
                    or recovered.policy != evaluation.policy
                    or recovered.triggered
                    or recovered.current.timestamp <= evaluation.current.timestamp
                    or recovered.current.comparison_scope_hash
                    != evaluation.current.comparison_scope_hash
                ):
                    raise DomainValidationError(
                        "Recovery must be later, comparable and within the same policy threshold"
                    )
                references.append(Reference.of(recovery))
        result = Snapshot(record, actual + 1, actor, timestamp, reason)
        self.repository.save(result, expected_revision, tuple(references))
        return result


def validate_write(
    snapshot: Snapshot, expected_revision: int, references: tuple[Reference, ...]
) -> None:
    """Adapter boundary validation, independent of database constraints."""
    if not isinstance(snapshot, Snapshot):
        raise DomainValidationError("A typed governance snapshot is required")
    integer(expected_revision)
    if snapshot.revision != expected_revision + 1:
        raise DomainValidationError("Snapshot must advance exactly one revision")
    require_tuple(references, Reference)
    keys = [(reference.kind, reference.entity_id) for reference in references]
    if len(set(keys)) != len(keys):
        raise DomainValidationError("Reference guards must be unique")
