"""Explicit schema-1 governance serialization; no pickle or inferred object loading."""

from datetime import date, datetime
from typing import Any

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain.governance.contracts import (
    Approval,
    Decision,
    Document,
    Finding,
    FindingStatus,
    Limitation,
    Lineage,
    Model,
    ModelStatus,
    Record,
    Version,
    identity,
)
from parallax_risk.domain.governance.monitoring import (
    Alert,
    AlertState,
    Evaluation,
    MonitorKind,
    Observation,
    Policy,
    Statistic,
)
from parallax_risk.domain.validation.contracts import Severity

type StoredRecord = Record | Policy | Evaluation | Alert


def record_key(record: StoredRecord) -> tuple[str, str]:
    if isinstance(record, Policy):
        return "policy", record.policy_id
    if isinstance(record, Evaluation):
        return "evaluation", record.evaluation_id
    if isinstance(record, Alert):
        return "alert", record.alert_id
    if not isinstance(record, (Model, Version, Finding, Approval, Limitation, Lineage)):
        raise DomainValidationError("Unsupported governance record type")
    return identity(record)


def encode(record: StoredRecord) -> Document:
    kind, _ = record_key(record)
    return Document.of({"schema": 1, "kind": kind, "record": record})


def _document(value: Any) -> Document:
    if (
        not isinstance(value, dict)
        or value.get("__type__") != "parallax_risk.domain.governance.contracts.Document"
        or set(value) != {"text", "__type__"}
    ):
        raise DomainValidationError("Invalid evidence document encoding")
    return Document(value["text"])


def _policy(data: dict[str, Any]) -> Policy:
    data = dict(data)
    data.pop("__type__")
    data["kind"] = MonitorKind(data["kind"])
    data["statistic"] = Statistic(data["statistic"])
    data["severity"] = Severity(data["severity"])
    return Policy(**data)


def _observation(data: dict[str, Any]) -> Observation:
    data = dict(data)
    data.pop("__type__")
    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    return Observation(**data)


def decode(document: Document) -> StoredRecord:
    """Reconstruct through domain constructors, checking the exact canonical encoding."""
    try:
        envelope: dict[str, Any] = document.value()
        if (
            set(envelope) != {"schema", "kind", "record"}
            or type(envelope["schema"]) is not int
            or envelope["schema"] != 1
        ):
            raise DomainValidationError("Unsupported governance schema")
        kind = envelope["kind"]
        data = dict(envelope["record"])
        data.pop("__type__")
        result: StoredRecord
        match kind:
            case "model":
                data["status"] = ModelStatus(data["status"])
                data["limitations"] = tuple(data["limitations"])
                data["last_validation"] = (
                    date.fromisoformat(data["last_validation"])
                    if data["last_validation"] is not None
                    else None
                )
                data["next_review"] = date.fromisoformat(data["next_review"])
                result = Model(**data)
            case "version":
                data["configuration"] = _document(data["configuration"])
                data["parameters"] = _document(data["parameters"])
                data["created"] = datetime.fromisoformat(data["created"])
                result = Version(**data)
            case "finding":
                data["severity"] = Severity(data["severity"])
                data["status"] = FindingStatus(data["status"])
                data["evidence"] = _document(data["evidence"])
                data["due_date"] = date.fromisoformat(data["due_date"])
                data["closure_evidence"] = (
                    _document(data["closure_evidence"])
                    if data["closure_evidence"] is not None
                    else None
                )
                result = Finding(**data)
            case "approval":
                data["decision"] = Decision(data["decision"])
                data["evidence"] = _document(data["evidence"])
                data["conditions"] = tuple(data["conditions"])
                data["decided"] = datetime.fromisoformat(data["decided"])
                result = Approval(**data)
            case "limitation":
                data["affected_portfolios"] = tuple(data["affected_portfolios"])
                data["compensating_controls"] = tuple(data["compensating_controls"])
                result = Limitation(**data)
            case "lineage":
                for key in ("sequence", "environment"):
                    data[key] = _document(data[key])
                for key in ("csa_versions", "assumptions"):
                    data[key] = tuple(data[key])
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                result = Lineage(**data)
            case "policy":
                result = _policy(envelope["record"])
            case "evaluation":
                data["policy"] = _policy(data["policy"])
                data["baseline"] = _observation(data["baseline"])
                data["current"] = _observation(data["current"])
                result = Evaluation(**data)
            case "alert":
                data["severity"] = Severity(data["severity"])
                data["state"] = AlertState(data["state"])
                data["evidence"] = _document(data["evidence"])
                result = Alert(**data)
            case _:
                raise DomainValidationError("Unknown governance record kind")
        if encode(result) != document:
            raise DomainValidationError("Noncanonical governance record encoding")
        return result
    except (KeyError, TypeError, ValueError) as error:
        raise DomainValidationError("Invalid governance record encoding") from error
