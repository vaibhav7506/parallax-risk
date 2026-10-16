"""Scalar monitoring with declared units, comparable scopes and explicit thresholds."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain._validation import require_text, require_token
from parallax_risk.domain.governance.contracts import Document, documents, enum_value, scope
from parallax_risk.domain.validation.contracts import Severity
from parallax_risk.domain.xva.contracts import fingerprint


class MonitorKind(StrEnum):
    PARAMETER = "parameter_drift"
    CALIBRATION = "calibration_error_drift"
    OUTPUT = "output_drift"
    PFE = "pfe_movement"
    CVA = "cva_movement"
    CONVERGENCE = "convergence_degradation"
    VALIDATION = "validation_rule_failures"


class Statistic(StrEnum):
    ABSOLUTE_CHANGE = "absolute_change"
    INCREASE = "increase"
    DECREASE = "decrease"
    LEVEL = "level"


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    model_id: str
    version_id: str
    kind: MonitorKind
    metric: str
    unit: str
    statistic: Statistic
    threshold: float
    severity: Severity
    rationale: str

    def __post_init__(self) -> None:
        scope(self.policy_id, self.model_id, self.version_id)
        require_token(self.metric)
        require_text(self.unit)
        require_text(self.rationale)
        enum_value(self.kind, MonitorKind)
        enum_value(self.statistic, Statistic)
        enum_value(self.severity, Severity)
        if require_finite(self.threshold, name="monitor threshold") < 0:
            raise DomainValidationError("Monitoring threshold must be nonnegative")
        if self.kind == MonitorKind.VALIDATION and (
            self.unit != "count" or self.statistic != Statistic.LEVEL
        ):
            raise DomainValidationError("Validation failures use a count level")


@dataclass(frozen=True, slots=True)
class Observation:
    metric: str
    unit: str
    value: float
    comparison_scope_hash: str
    evidence_hash: str
    timestamp: datetime

    def __post_init__(self) -> None:
        require_token(self.metric)
        require_text(self.unit)
        require_finite(self.value, name="monitor observation")
        fingerprint(self.comparison_scope_hash)
        fingerprint(self.evidence_hash)
        object.__setattr__(self, "timestamp", utc_timestamp(self.timestamp))


@dataclass(frozen=True, slots=True)
class Evaluation:
    evaluation_id: str
    policy: Policy
    baseline: Observation
    current: Observation

    def __post_init__(self) -> None:
        require_token(self.evaluation_id)
        if (
            not isinstance(self.policy, Policy)
            or not isinstance(self.baseline, Observation)
            or not isinstance(self.current, Observation)
        ):
            raise DomainValidationError("Typed policy and observations are required")
        for observation in (self.baseline, self.current):
            if (observation.metric, observation.unit) != (self.policy.metric, self.policy.unit):
                raise DomainValidationError("Monitoring metric and units must match the policy")
            if self.policy.kind == MonitorKind.VALIDATION and (
                observation.value < 0 or observation.value != int(observation.value)
            ):
                raise DomainValidationError(
                    "Validation failure count must be a nonnegative integer"
                )
        if self.baseline.comparison_scope_hash != self.current.comparison_scope_hash:
            raise DomainValidationError("Monitoring comparison scopes must match")
        if self.current.timestamp <= self.baseline.timestamp:
            raise DomainValidationError("Monitoring requires a later current observation")
        require_finite(self.statistic, name="monitor statistic")

    @property
    def model_id(self) -> str:
        return self.policy.model_id

    @property
    def version_id(self) -> str:
        return self.policy.version_id

    @property
    def statistic(self) -> float:
        delta = self.current.value - self.baseline.value
        match self.policy.statistic:
            case Statistic.ABSOLUTE_CHANGE:
                return abs(delta)
            case Statistic.INCREASE:
                return delta
            case Statistic.DECREASE:
                return -delta
            case Statistic.LEVEL:
                return self.current.value

    @property
    def triggered(self) -> bool:
        """Strict exceedance; equality is within the caller's declared threshold."""
        return self.statistic > self.policy.threshold


class AlertState(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: str
    model_id: str
    version_id: str
    evaluation_id: str
    severity: Severity
    state: AlertState
    evidence: Document
    resolution_evaluation_id: str | None = None

    def __post_init__(self) -> None:
        scope(self.alert_id, self.model_id, self.version_id)
        require_token(self.evaluation_id)
        enum_value(self.severity, Severity)
        enum_value(self.state, AlertState)
        documents(self.evidence)
        if self.state == AlertState.RESOLVED:
            if self.resolution_evaluation_id is None:
                raise DomainValidationError("Resolved alerts require a recovery evaluation")
            require_token(self.resolution_evaluation_id)
        elif self.resolution_evaluation_id is not None:
            raise DomainValidationError("Only resolved alerts reference recovery evaluations")
