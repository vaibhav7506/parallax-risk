"""Comparable metric schemas, tolerances and reproducible findings; no approval state."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.pricing._numbers import total
from parallax_risk.domain.xva.contracts import fingerprint


@dataclass(frozen=True, slots=True)
class Contribution:
    name: str
    value: float

    def __post_init__(self) -> None:
        require_token(self.name)
        require_finite(self.value, name="metric contribution")


@dataclass(frozen=True, slots=True)
class Metric:
    """Binary64 scalar with exact unit label; additive components may leave a residual."""

    name: str
    value: float
    unit: str
    contributions: tuple[Contribution, ...] = ()

    def __post_init__(self) -> None:
        require_token(self.name)
        require_finite(self.value, name="metric")
        require_text(self.unit)
        require_tuple(self.contributions, Contribution)
        if len({c.name for c in self.contributions}) != len(self.contributions):
            raise DomainValidationError("Metric contribution names must be unique")

    @property
    def schema(self) -> tuple[str, str, tuple[str, ...]]:
        return self.name, self.unit, tuple(c.name for c in self.contributions)


@dataclass(frozen=True, slots=True)
class ModelOutput:
    case_hash: str
    model_name: str
    model_version: str
    metrics: tuple[Metric, ...]
    evidence_hash: str
    assumptions: tuple[str, ...]

    def __post_init__(self) -> None:
        fingerprint(self.case_hash)
        fingerprint(self.evidence_hash)
        require_token(self.model_name)
        require_text(self.model_version)
        require_tuple(self.metrics, Metric, nonempty=True)
        require_tuple(self.assumptions, str, nonempty=True)
        for assumption in self.assumptions:
            require_text(assumption)
        if len({m.name for m in self.metrics}) != len(self.metrics):
            raise DomainValidationError("Model metrics must be unique")

    def metric(self, name: str) -> Metric:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        raise DomainValidationError("Model does not supply the requested metric")

    @property
    def hash(self) -> str:
        return content_hash(self)


@dataclass(frozen=True, slots=True)
class Tolerance:
    """Absolute metric units plus relative fraction of the declared reference magnitude."""

    absolute: float
    relative: float = 0.0

    def __post_init__(self) -> None:
        if any(require_finite(v, name="tolerance") < 0 for v in (self.absolute, self.relative)):
            raise DomainValidationError("Tolerances cannot be negative")

    def bound(self, reference: float) -> float:
        return require_finite(
            self.absolute + self.relative * abs(require_finite(reference, name="reference")),
            name="tolerance bound",
        )


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    severity: Severity
    evidence: tuple[str, ...]
    affected_metric: str
    reproduction: str
    model_version: str
    status: FindingStatus = FindingStatus.OPEN

    def __post_init__(self) -> None:
        require_token(self.finding_id)
        require_token(self.affected_metric)
        require_text(self.reproduction)
        require_text(self.model_version)
        require_tuple(self.evidence, str, nonempty=True)
        for item in self.evidence:
            require_text(item)
        if not isinstance(self.severity, Severity) or not isinstance(self.status, FindingStatus):
            raise DomainValidationError("Finding severity and status must be typed")


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    metric: str
    passed: bool
    observed: float
    allowed: float
    evidence: tuple[str, ...]
    finding: Finding | None


def check(
    name: str,
    metric: Metric,
    observed: float,
    allowed: float,
    *,
    evidence: tuple[str, ...],
    reproduction: str,
    version: str,
    severity: Severity = Severity.HIGH,
) -> Check:
    """Record an absolute discrepancy; failures become immutable open findings."""
    require_token(name)
    if not isinstance(metric, Metric):
        raise DomainValidationError("Check requires a typed metric")
    if (
        require_finite(observed, name="discrepancy") < 0
        or require_finite(allowed, name="bound") < 0
    ):
        raise DomainValidationError("Discrepancy and bound must be nonnegative")
    # Construct even on success to validate all supplied evidence and provenance.
    finding = Finding(name, severity, evidence, metric.name, reproduction, version)
    passed = observed <= allowed
    return Check(
        name, metric.name, passed, observed, allowed, evidence, None if passed else finding
    )


@dataclass(frozen=True, slots=True)
class MetricDifference:
    name: str
    unit: str
    production: float
    challenger: float
    difference: float
    contributions: tuple[Contribution, ...]
    residual: float
    check: Check


@dataclass(frozen=True, slots=True)
class Comparison:
    production: ModelOutput
    challenger: ModelOutput
    differences: tuple[MetricDifference, ...]


def compare(
    production: ModelOutput, challenger: ModelOutput, tolerance: Tolerance, reproduction: str
) -> Comparison:
    """Challenger minus production; require identical input and ordered metric schemas."""
    if (
        not isinstance(production, ModelOutput)
        or not isinstance(challenger, ModelOutput)
        or not isinstance(tolerance, Tolerance)
        or production.case_hash != challenger.case_hash
        or tuple(m.schema for m in production.metrics)
        != tuple(m.schema for m in challenger.metrics)
    ):
        raise DomainValidationError("Comparison requires same inputs and exact metric/unit schemas")
    differences = []
    for p, c in zip(production.metrics, challenger.metrics, strict=True):
        difference = total((c.value, -p.value))
        parts = tuple(
            Contribution(a.name, total((b.value, -a.value)))
            for a, b in zip(p.contributions, c.contributions, strict=True)
        )
        residual = total((difference, -total(tuple(v.value for v in parts))))
        result = check(
            f"comparison-{p.name}",
            p,
            abs(difference),
            tolerance.bound(c.value),
            evidence=(production.hash, challenger.hash, f"unit={p.unit}; challenger-production"),
            reproduction=reproduction,
            version=production.model_version,
        )
        differences.append(
            MetricDifference(p.name, p.unit, p.value, c.value, difference, parts, residual, result)
        )
    return Comparison(production, challenger, tuple(differences))
