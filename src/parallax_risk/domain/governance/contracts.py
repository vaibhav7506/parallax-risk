"""Immutable inventory, governance evidence and risk-run lineage contracts."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from parallax_risk.common.canonical import JsonValue, canonical_value, content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.time import require_date, utc_timestamp
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.validation.contracts import Severity
from parallax_risk.domain.xva.contracts import fingerprint


def integer(value: int, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise DomainValidationError("Expected an integer within the declared range")


def texts(values: tuple[str, ...], *, nonempty: bool = False) -> None:
    require_tuple(values, str, nonempty=nonempty)
    for value in values:
        require_text(value)
    if len(set(values)) != len(values):
        raise DomainValidationError("Metadata entries must be unique")


def enum_value(value: object, kind: type[StrEnum]) -> None:
    if not isinstance(value, kind):
        raise DomainValidationError("An explicit governance enum is required")


def _pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise DomainValidationError("Duplicate JSON keys are not permitted")
        result[key] = value
    return result


def _immutable_json(value: JsonValue) -> object:
    """Freeze arrays produced by our JSON parser before using the strict canonicalizer."""
    if isinstance(value, list):
        return tuple(_immutable_json(item) for item in value)
    if isinstance(value, dict):
        return {key: _immutable_json(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class Document:
    """Canonical UTF-8 JSON object stored as immutable text, never a mutable dict.

    Read access returns a fresh object. NaN, duplicate keys and non-object roots fail.
    The digest is a content fingerprint, not a signature or proof of authenticity.
    """

    text: str

    def __post_init__(self) -> None:
        require_text(self.text)
        try:
            value = json.loads(self.text, object_pairs_hook=_pairs)
        except (ValueError, RecursionError) as error:
            raise DomainValidationError("Invalid JSON document") from error
        if not isinstance(value, dict):
            raise DomainValidationError("Evidence must be a JSON object")
        encoded = json.dumps(
            canonical_value(_immutable_json(value)),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        object.__setattr__(self, "text", encoded)

    @classmethod
    def of(cls, value: object) -> "Document":
        return cls(json.dumps(canonical_value(value), allow_nan=False))

    def value(self) -> dict[str, JsonValue]:
        value: dict[str, JsonValue] = json.loads(self.text)
        return value

    @property
    def hash(self) -> str:
        return content_hash(_immutable_json(self.value()))


class ModelStatus(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    ACTIVE = "active"
    RETIRED = "retired"


class FindingStatus(StrEnum):
    OPEN = "open"
    REMEDIATING = "remediating"
    CLOSED = "closed"


class Decision(StrEnum):
    APPROVE = "approve"
    CONDITIONAL = "conditional"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class Model:
    model_id: str
    name: str
    model_type: str
    owner: str
    purpose: str
    status: ModelStatus
    version: str
    methodology: str
    limitations: tuple[str, ...]
    materiality: str
    validation_frequency_days: int
    last_validation: date | None
    next_review: date

    def __post_init__(self) -> None:
        require_token(self.model_id)
        for value in (
            self.name,
            self.model_type,
            self.owner,
            self.purpose,
            self.version,
            self.methodology,
            self.materiality,
        ):
            require_text(value)
        enum_value(self.status, ModelStatus)
        texts(self.limitations)
        integer(self.validation_frequency_days, 1)
        require_date(self.next_review)
        if self.last_validation is not None:
            require_date(self.last_validation)
            if self.next_review <= self.last_validation:
                raise DomainValidationError("Next review must follow last validation")


@dataclass(frozen=True, slots=True)
class Version:
    version_id: str
    model_id: str
    label: str
    code_reference: str
    configuration: Document
    parameters: Document
    created: datetime

    def __post_init__(self) -> None:
        require_token(self.version_id)
        require_token(self.model_id)
        require_text(self.label)
        require_text(self.code_reference)
        documents(self.configuration, self.parameters)
        object.__setattr__(self, "created", utc_timestamp(self.created))


def documents(*values: Document) -> None:
    if any(not isinstance(value, Document) for value in values):
        raise DomainValidationError("Immutable evidence documents are required")


def scope(record_id: str, model_id: str, version_id: str) -> None:
    for value in (record_id, model_id, version_id):
        require_token(value)


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    model_id: str
    version_id: str
    severity: Severity
    description: str
    evidence: Document
    owner: str
    due_date: date
    status: FindingStatus = FindingStatus.OPEN
    remediation: str | None = None
    closure_evidence: Document | None = None

    def __post_init__(self) -> None:
        scope(self.finding_id, self.model_id, self.version_id)
        enum_value(self.severity, Severity)
        enum_value(self.status, FindingStatus)
        require_text(self.description)
        require_text(self.owner)
        require_date(self.due_date)
        documents(self.evidence)
        if self.remediation is not None:
            require_text(self.remediation)
        if self.status != FindingStatus.OPEN and self.remediation is None:
            raise DomainValidationError("Remediation text is required after the open state")
        if self.status == FindingStatus.CLOSED:
            if self.closure_evidence is None:
                raise DomainValidationError("Closing a finding requires evidence")
            documents(self.closure_evidence)
        elif self.closure_evidence is not None:
            raise DomainValidationError("Closure evidence belongs only to a closed finding")


@dataclass(frozen=True, slots=True)
class Approval:
    approval_id: str
    model_id: str
    version_id: str
    decision: Decision
    rationale: str
    evidence: Document
    conditions: tuple[str, ...]
    authority: str
    decided: datetime

    def __post_init__(self) -> None:
        scope(self.approval_id, self.model_id, self.version_id)
        enum_value(self.decision, Decision)
        for value in (self.rationale, self.authority):
            require_text(value)
        documents(self.evidence)
        texts(self.conditions)
        if (self.decision == Decision.CONDITIONAL) != bool(self.conditions):
            raise DomainValidationError("Only conditional approval requires explicit conditions")
        object.__setattr__(self, "decided", utc_timestamp(self.decided))


@dataclass(frozen=True, slots=True)
class Limitation:
    limitation_id: str
    model_id: str
    version_id: str
    description: str
    affected_portfolios: tuple[str, ...]
    materiality: str
    compensating_controls: tuple[str, ...]

    def __post_init__(self) -> None:
        scope(self.limitation_id, self.model_id, self.version_id)
        require_text(self.description)
        require_text(self.materiality)
        texts(self.affected_portfolios, nonempty=True)
        texts(self.compensating_controls, nonempty=True)
        for digest in self.affected_portfolios:
            fingerprint(digest)


@dataclass(frozen=True, slots=True)
class Lineage:
    run_id: str
    model_id: str
    version_id: str
    code_revision: str | None
    portfolio_hash: str
    market_data_hash: str
    configuration_hash: str
    calibration_id: str | None
    seed: int | None
    sequence: Document
    csa_versions: tuple[str, ...]
    timestamp: datetime
    environment: Document
    result_hash: str
    assumptions: tuple[str, ...]

    def __post_init__(self) -> None:
        scope(self.run_id, self.model_id, self.version_id)
        for digest in (
            self.portfolio_hash,
            self.market_data_hash,
            self.configuration_hash,
            self.result_hash,
        ):
            fingerprint(digest)
        for value in (self.code_revision, self.calibration_id):
            if value is not None:
                require_text(value)
        if self.seed is not None:
            integer(self.seed)
            if self.seed >= 2**64:
                raise DomainValidationError("Seed must fit uint64")
        documents(self.sequence, self.environment)
        texts(self.csa_versions)
        for digest in self.csa_versions:
            fingerprint(digest)
        texts(self.assumptions, nonempty=True)
        object.__setattr__(self, "timestamp", utc_timestamp(self.timestamp))


type Record = Model | Version | Finding | Approval | Limitation | Lineage


def identity(record: Record) -> tuple[str, str]:
    match record:
        case Model():
            return "model", record.model_id
        case Version():
            return "version", record.version_id
        case Finding():
            return "finding", record.finding_id
        case Approval():
            return "approval", record.approval_id
        case Limitation():
            return "limitation", record.limitation_id
        case Lineage():
            return "lineage", record.run_id


def finding_transition(before: Finding, after: Finding) -> None:
    """Only OPEN -> REMEDIATING -> CLOSED; immutable scope and original evidence."""
    immutable = (
        "finding_id",
        "model_id",
        "version_id",
        "severity",
        "description",
        "evidence",
        "owner",
        "due_date",
    )
    if any(getattr(before, key) != getattr(after, key) for key in immutable):
        raise DomainValidationError(
            "Finding identity, ownership and opening evidence cannot change"
        )
    allowed = {
        FindingStatus.OPEN: FindingStatus.REMEDIATING,
        FindingStatus.REMEDIATING: FindingStatus.CLOSED,
    }
    if allowed.get(before.status) != after.status:
        raise DomainValidationError("Invalid finding state transition")
