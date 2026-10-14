"""Sourced historical shock ingestion and actual hypothetical/combined XVA revaluation."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from parallax_risk.application.validation_models import ProductionXvaModel
from parallax_risk.application.xva_revaluation import FactorMove, XvaExperiment
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.pricing._numbers import total
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.validation.contracts import Contribution, ModelOutput
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor


def factor_unit(factor: RiskFactor) -> str:
    return {
        FactorKind.RATE: "annual_decimal_rate",
        FactorKind.FX: "direct_quote_per_base",
        FactorKind.VOLATILITY: "declared_model_volatility",
        FactorKind.CREDIT_SPREAD: "annual_decimal_credit_triangle_spread",
        FactorKind.RECOVERY: "recovery_fraction",
        FactorKind.CORRELATION: "brownian_correlation",
        FactorKind.COLLATERAL: "CSA_currency_receive_threshold",
    }[factor.kind]


class ScenarioKind(StrEnum):
    HYPOTHETICAL = "hypothetical"
    HISTORICAL = "historical_shock_replay"
    COMBINED = "combined_ordered_shocks"


@dataclass(frozen=True, slots=True)
class StressScenario:
    name: str
    kind: ScenarioKind
    moves: tuple[FactorMove, ...]
    source: str
    description: str
    start_date: date | None = None
    end_date: date | None = None
    parents: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_token(self.name)
        require_text(self.source)
        require_text(self.description)
        require_tuple(self.moves, FactorMove, nonempty=True)
        require_tuple(self.parents, str)
        for parent in self.parents:
            require_text(parent)
        if not isinstance(self.kind, ScenarioKind) or len({m.name for m in self.moves}) != len(
            self.moves
        ):
            raise DomainValidationError("Stress kind must be typed and movement names unique")
        if self.kind == ScenarioKind.HISTORICAL:
            if (
                type(self.start_date) is not date
                or type(self.end_date) is not date
                or self.start_date >= self.end_date
            ):
                raise DomainValidationError(
                    "Historical stress requires an ordered observed date interval"
                )
        elif self.start_date is not None or self.end_date is not None:
            raise DomainValidationError("Only historical scenarios carry observed dates")
        if self.kind == ScenarioKind.COMBINED and len(self.parents) < 2:
            raise DomainValidationError("Combined stress requires parent scenario provenance")
        if self.kind != ScenarioKind.COMBINED and self.parents:
            raise DomainValidationError("Parent scenarios only apply to combined stress")

    @property
    def hash(self) -> str:
        return content_hash(self)


@dataclass(frozen=True, slots=True)
class HistoricalObservation:
    name: str
    factor: RiskFactor
    before: float
    after: float
    unit: str

    def __post_init__(self) -> None:
        require_token(self.name)
        if not isinstance(self.factor, RiskFactor) or self.unit != factor_unit(self.factor):
            raise DomainValidationError("Historical observation must match exact factor units")
        require_finite(self.before, name="historical before")
        require_finite(self.after, name="historical after")


def historical_scenario(
    name: str,
    observations: tuple[HistoricalObservation, ...],
    start: date,
    end: date,
    source: str,
    description: str,
) -> StressScenario:
    """Caller-sourced parameter observations; no fabricated history or automatic data feed."""
    require_tuple(observations, HistoricalObservation, nonempty=True)
    moves = tuple(FactorMove(o.name, o.factor, total((o.after, -o.before))) for o in observations)
    return StressScenario(name, ScenarioKind.HISTORICAL, moves, source, description, start, end)


def combine(name: str, scenarios: tuple[StressScenario, ...], description: str) -> StressScenario:
    require_tuple(scenarios, StressScenario, nonempty=True)
    if len(scenarios) < 2 or len({s.name for s in scenarios}) != len(scenarios):
        raise DomainValidationError("Combined stress needs distinct parent scenarios")
    moves = tuple(
        FactorMove(f"{i}-{m.name}", m.factor, m.amount)
        for i, s in enumerate(scenarios)
        for m in s.moves
    )
    return StressScenario(
        name,
        ScenarioKind.COMBINED,
        moves,
        "Ordered combination of retained scenario hashes",
        description,
        parents=tuple(s.hash for s in scenarios),
    )


@dataclass(frozen=True, slots=True)
class StressResult:
    scenario: StressScenario
    baseline: ModelOutput
    stressed: ModelOutput
    changes: tuple[Contribution, ...]
    movement_units: tuple[str, ...]
    interpretation: str = (
        "Actual ordered absolute parameter shocks; fixed funding/IM/fixings; "
        "no event likelihood inferred"
    )


def stress(
    model: ProductionXvaModel,
    baseline: XvaExperiment,
    scenarios: tuple[StressScenario, ...],
    *,
    maximum_evaluations: int = 100,
) -> tuple[StressResult, ...]:
    require_tuple(scenarios, StressScenario, nonempty=True)
    integer(maximum_evaluations, "stress evaluation budget")
    if len(scenarios) + 1 > maximum_evaluations or len({s.name for s in scenarios}) != len(
        scenarios
    ):
        raise DomainValidationError("Stress evaluation budget or unique scenario names violated")
    original = model.evaluate(baseline)
    results = []
    for scenario in scenarios:
        changed = baseline
        for move in scenario.moves:
            changed = model.workflow.bump(changed, move.factor, move.amount)
        result = model.evaluate(changed)
        if (result.model_name, result.model_version) != (
            original.model_name,
            original.model_version,
        ) or tuple(m.schema for m in result.metrics) != tuple(m.schema for m in original.metrics):
            raise DomainValidationError("Stress revaluation changed model or metric schemas")
        changes = tuple(
            Contribution(a.name, total((b.value, -a.value)))
            for a, b in zip(original.metrics, result.metrics, strict=True)
        )
        results.append(
            StressResult(
                scenario,
                original,
                result,
                changes,
                tuple(factor_unit(m.factor) for m in scenario.moves),
            )
        )
    return tuple(results)
