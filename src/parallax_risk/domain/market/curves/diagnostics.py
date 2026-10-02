"""Explicit curve diagnostics; increasing discounts are evidence, not always errors."""

from dataclasses import dataclass

from parallax_risk.domain.market.curves.term_structures import DiscountCurve


@dataclass(frozen=True, slots=True)
class CurveDiagnostics:
    """Finite/positive anchor sanity is enforced at construction; monotonicity is reported."""

    curve_hash: str
    node_count: int
    minimum_discount: float
    maximum_discount: float
    nonincreasing_discounts: bool
    increasing_intervals: tuple[int, ...]
    continuous_zero_rates: tuple[float, ...]


def diagnose_curve(curve: DiscountCurve) -> CurveDiagnostics:
    """Report knot discounts and zero rates without forbidding valid negative rates."""
    increasing = tuple(
        index
        for index, (left, right) in enumerate(
            zip(curve.discount_factors, curve.discount_factors[1:], strict=False)
        )
        if right > left
    )
    return CurveDiagnostics(
        curve.curve_hash,
        len(curve.times),
        min(curve.discount_factors),
        max(curve.discount_factors),
        not increasing,
        increasing,
        tuple(curve.continuous_zero_rate(time) for time in curve.times[1:]),
    )
