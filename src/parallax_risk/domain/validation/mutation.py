"""Explicit controlled faults and baseline-qualified detection evidence."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain._validation import require_text, require_token
from parallax_risk.domain.validation.contracts import Check, ModelOutput


class MutationKind(StrEnum):
    DISCOUNT = "discount_factor_error"
    SIGN = "sign_convention_error"
    RECOVERY = "wrong_recovery"
    FX = "wrong_FX_conversion"
    DAY_COUNT = "incorrect_day_count"
    CORRELATION = "correlation_sign_error"
    COLLATERAL = "missing_collateral"
    THRESHOLD = "incorrect_threshold"
    DATE = "off_by_one_exposure_date"
    LOOK_AHEAD = "look_ahead_calibration"
    VOLATILITY = "volatility_scaling_error"
    PATHS = "insufficient_path_count"
    INTERPOLATION = "interpolation_defect"
    MPOR = "ignored_MPOR"
    DEFAULT = "default_probability_misuse"


@dataclass(frozen=True, slots=True)
class Mutation:
    name: str
    kind: MutationKind
    category: str
    description: str

    def __post_init__(self) -> None:
        require_token(self.name)
        require_token(self.category)
        require_text(self.description)
        if not isinstance(self.kind, MutationKind):
            raise DomainValidationError("Mutation requires a typed controlled fault")


@dataclass(frozen=True, slots=True)
class MutationEvidence:
    mutation: Mutation
    output: ModelOutput
    checks: tuple[Check, ...]
    newly_failed: tuple[str, ...]
    detected: bool


@dataclass(frozen=True, slots=True)
class DetectionRate:
    category: str
    detected: int
    executed: int
    rate: float


@dataclass(frozen=True, slots=True)
class MutationCampaign:
    baseline: ModelOutput
    baseline_checks: tuple[Check, ...]
    evidence: tuple[MutationEvidence, ...]
    rates: tuple[DetectionRate, ...]
    reproduction: str
    interpretation: str = (
        "Detection is a new failed baseline-passing check; misses retained. "
        "Rate applies only to these explicit faults, cases and selected checks."
    )
