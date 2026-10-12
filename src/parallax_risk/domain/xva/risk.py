"""Actual component finite differences and ordered movement attribution with residuals."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.pricing._numbers import money_value, product, total
from parallax_risk.domain.xva.contracts import ComponentKind, XvaResult


class FactorKind(StrEnum):
    RATE = "rate"
    FX = "fx"
    VOLATILITY = "volatility"
    CREDIT_SPREAD = "credit_spread"
    RECOVERY = "recovery"
    CORRELATION = "correlation"
    COLLATERAL = "collateral_receive_threshold"


@dataclass(frozen=True, slots=True)
class RiskFactor:
    """Exact component/counterparty/scope target, plus second driver for correlation."""

    kind: FactorKind
    target: str
    second: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FactorKind):
            raise DomainValidationError("Risk factor kind must be typed")
        require_token(self.target)
        if self.kind == FactorKind.CORRELATION:
            if self.second is None or self.second == self.target:
                raise DomainValidationError("Correlation requires two different named drivers")
            require_token(self.second)
        elif self.second is not None:
            raise DomainValidationError("Second target only applies to correlation")


@dataclass(frozen=True, slots=True)
class ComponentSensitivity:
    kind: str
    derivative_per_unit: float
    half_bump_derivative: float
    absolute_stability_difference: float


@dataclass(frozen=True, slots=True)
class XvaSensitivity:
    factor: RiskFactor
    bump: float
    units: str
    base: XvaResult
    up: XvaResult
    down: XvaResult
    half_up: XvaResult
    half_down: XvaResult
    components: tuple[ComponentSensitivity, ...]
    methodology: str = "central differences h and h/2; same addressed market/default/rank streams"


def _values(result: XvaResult) -> tuple[float, ...]:
    return tuple(money_value(c.adjustment) for c in result.components) + (
        money_value(result.total_adjustment),
    )


def sensitivity(
    factor: RiskFactor, bump: float, units: str, revalue: Callable[[float], XvaResult]
) -> XvaSensitivity:
    """Revalue real inputs at 0, +/-h and +/-h/2; report actual stability, no certification.

    All bumps must be admissible; no one-sided fallback, projection or correlation repair.
    Sampling/grid/kink effects can make differences unstable despite common random numbers.
    """
    if not isinstance(factor, RiskFactor):
        raise DomainValidationError("Sensitivity needs validated risk factor")
    bump = require_finite(bump, name="XVA bump")
    if bump <= 0 or bump * 0.5 == 0:
        raise DomainValidationError("Central bump must be strictly positive and resolved")
    require_text(units)
    base, up, down, half_up, half_down = (
        revalue(v) for v in (0.0, bump, -bump, bump * 0.5, -bump * 0.5)
    )
    results = (base, up, down, half_up, half_down)
    if any(not isinstance(r, XvaResult) or r.currency != base.currency for r in results):
        raise DomainValidationError("Revaluation results must share reporting currency")
    if any(r.input_hash == base.input_hash for r in results[1:]):
        raise DomainValidationError("Bump did not change validated valuation inputs")
    output = []
    for kind, a, b, c, d in zip(
        (*ComponentKind, "TOTAL"),
        _values(up),
        _values(down),
        _values(half_up),
        _values(half_down),
        strict=True,
    ):
        derivative = require_finite(total((a, -b)) / product(2.0, bump), name="XVA derivative")
        half = require_finite(total((c, -d)) / bump, name="half-bump derivative")
        output.append(
            ComponentSensitivity(str(kind), derivative, half, abs(total((derivative, -half))))
        )
    return XvaSensitivity(factor, bump, units, base, up, down, half_up, half_down, tuple(output))


@dataclass(frozen=True, slots=True)
class AttributionStep:
    name: str
    component_movements: tuple[float, ...]
    total_movement: float
    before_hash: str
    after_hash: str


@dataclass(frozen=True, slots=True)
class XvaAttribution:
    """Ordered exact revaluation ladder; interactions are order dependent, residual explicit."""

    baseline: XvaResult
    actual: XvaResult
    steps: tuple[AttributionStep, ...]
    component_changes: tuple[float, ...]
    component_residuals: tuple[float, ...]
    total_change: float
    explained_change: float
    unexplained_change: float
    methodology: str = "ordered_sequential_exact_revaluation; not Shapley allocation"


def attribute(
    baseline: XvaResult, ladder: tuple[tuple[str, XvaResult], ...], actual: XvaResult
) -> XvaAttribution:
    """Reconcile each factor's four signed components and actual end minus ladder end."""
    if (
        not isinstance(baseline, XvaResult)
        or not isinstance(actual, XvaResult)
        or actual.currency != baseline.currency
    ):
        raise DomainValidationError("Attribution requires same-currency baseline/end results")
    require_tuple(ladder, tuple)
    if any(len(pair) != 2 for pair in ladder):
        raise DomainValidationError("Each attribution step requires a name and result")
    previous = baseline
    output = []
    names: set[str] = set()
    for name, result in ladder:
        require_token(name)
        if (
            name in names
            or not isinstance(result, XvaResult)
            or result.currency != baseline.currency
        ):
            raise DomainValidationError("Attribution steps must be unique and same-currency")
        names.add(name)
        movements = tuple(
            total((b, -a))
            for a, b in zip(_values(previous)[:-1], _values(result)[:-1], strict=True)
        )
        output.append(
            AttributionStep(
                name,
                movements,
                total(
                    (money_value(result.total_adjustment), -money_value(previous.total_adjustment))
                ),
                previous.hash,
                result.hash,
            )
        )
        previous = result
    changes = tuple(
        total((b, -a)) for a, b in zip(_values(baseline)[:-1], _values(actual)[:-1], strict=True)
    )
    residuals = tuple(
        total((b, -a)) for a, b in zip(_values(previous)[:-1], _values(actual)[:-1], strict=True)
    )
    changed = total((money_value(actual.total_adjustment), -money_value(baseline.total_adjustment)))
    explained = total(tuple(s.total_movement for s in output))
    residual = total(
        (money_value(actual.total_adjustment), -money_value(previous.total_adjustment))
    )
    return XvaAttribution(
        baseline, actual, tuple(output), changes, residuals, changed, explained, residual
    )
