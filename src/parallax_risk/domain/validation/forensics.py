"""Fingerprint changes and ordered arithmetic evidence, never causal certification."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.domain.validation.contracts import Check, ModelOutput
from parallax_risk.domain.xva.contracts import fingerprint


class CauseKind(StrEnum):
    MARKET = "market_movement"
    PORTFOLIO = "portfolio_movement"
    CALIBRATION = "calibration_movement"
    VERSION = "model_version"
    PARAMETERS = "parameter_drift"
    NUMERICS = "numerical_instability"
    COLLATERAL = "collateral_change"


@dataclass(frozen=True, slots=True)
class DiagnosticContext:
    market: str
    portfolio: str
    calibration: str
    parameters: str
    numerics: str
    collateral: str

    def __post_init__(self) -> None:
        for value in (
            self.market,
            self.portfolio,
            self.calibration,
            self.parameters,
            self.numerics,
            self.collateral,
        ):
            fingerprint(value)


@dataclass(frozen=True, slots=True)
class DiagnosticCause:
    kind: CauseKind
    changed: bool
    before: str
    after: str
    interpretation: str


@dataclass(frozen=True, slots=True)
class DiagnosticStep:
    name: str
    possible_cause: CauseKind
    output: ModelOutput
    context: DiagnosticContext
    change: float


@dataclass(frozen=True, slots=True)
class ForensicReport:
    metric: str
    unit: str
    before: ModelOutput
    after: ModelOutput
    before_context: DiagnosticContext
    after_context: DiagnosticContext
    change: float
    materiality: Check
    causes: tuple[DiagnosticCause, ...]
    steps: tuple[DiagnosticStep, ...]
    residual: float
    repeats: tuple[ModelOutput, ModelOutput]
    repeat_checks: tuple[Check, Check]
    reproduction: str
    interpretation: str = (
        "Changed fingerprints identify possible causes, not causal proof. "
        "Caller-labelled ordered counterfactual valuations can overlap; order matters. "
        "Endpoint minus ordered arithmetic bridge remains an explicit residual. "
        "Repeatability checks do not prove numerical accuracy or convergence."
    )
