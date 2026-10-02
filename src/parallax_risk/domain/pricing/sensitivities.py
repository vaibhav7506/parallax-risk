"""Central finite differences with declared bump units, scope, signs and input evidence."""

from dataclasses import dataclass, replace

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import PricingError
from parallax_risk.common.identifiers import CurveId, MarketSnapshotVersion
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain.instruments.fx.contracts import FxForward
from parallax_risk.domain.pricing._numbers import money_value, priced_money, product, total
from parallax_risk.domain.pricing.engine import DiscountingEngine, Instrument, PricingContext
from parallax_risk.domain.pricing.results import PricingResult

ONE_BASIS_POINT = 1e-4


@dataclass(frozen=True, slots=True)
class RateSensitivity:
    """Derivative per unit decimal annual rate; PV01 signed, DV01 = -PV01."""

    base: PricingResult
    up: PricingResult
    down: PricingResult
    bump_size: float
    curve_ids: tuple[CurveId, ...]
    derivative_per_unit_rate: float
    pv01: Money
    dv01: Money
    methodology: str = (
        "Central difference of continuous-zero knot shifts; fixed market quotes/fixings."
    )


@dataclass(frozen=True, slots=True)
class FxDelta:
    """QUOTE-currency NPV derivative per one QUOTE/BASE spot-rate unit."""

    base: PricingResult
    up: PricingResult
    down: PricingResult
    bump_size: float
    derivative_per_spot_unit: float
    methodology: str = "Central difference of direct settlement-date FX spot; fixed curves."


def _bump(value: float) -> float:
    result = require_finite(value, name="finite-difference bump")
    if result <= 0:
        raise PricingError("Finite-difference bump size must be strictly positive")
    return result


def _derivative(up: PricingResult, down: PricingResult, bump: float) -> float:
    value = total((money_value(up.npv), -money_value(down.npv))) / product(2.0, bump)
    return require_finite(value, name="finite-difference derivative")


def parallel_rate_sensitivity(
    instrument: Instrument,
    context: PricingContext,
    *,
    curve_ids: tuple[CurveId, ...],
    bump_size: float,
) -> RateSensitivity:
    """Bump explicitly selected discount/projection curves, holding observed fixings fixed.

    This is zero-knot PV01/DV01, not calibrated market-quote sensitivity. A shared
    curve ID is bumped consistently in discounting and projection assignments.
    """
    bump = _bump(bump_size)
    engine = DiscountingEngine()
    base = engine.price(instrument, context)
    up_curves = context.curves.bumped(curve_ids, bump)
    down_curves = context.curves.bumped(curve_ids, -bump)
    if context.curves.curve_hash in (up_curves.curve_hash, down_curves.curve_hash):
        raise PricingError("Rate bump is smaller than binary64 resolution")
    up = engine.price(instrument, replace(context, curves=up_curves))
    down = engine.price(instrument, replace(context, curves=down_curves))
    derivative = _derivative(up, down, bump)
    pv01 = priced_money(product(derivative, ONE_BASIS_POINT), base.currency)
    return RateSensitivity(base, up, down, bump, curve_ids, derivative, pv01, -pv01)


def fx_delta(instrument: FxForward, context: PricingContext, *, bump_size: float) -> FxDelta:
    """Revalue a deliverable FX forward with central direct-spot bumps; no cross-rate synthesis."""
    if not isinstance(instrument, FxForward):
        raise PricingError("FX delta requires an FX-forward contract")
    bump = _bump(bump_size)
    base_currency, quote_currency = instrument.base_notional.currency, instrument.quote_currency
    spot = context.snapshot.fx_spot(base_currency, quote_currency)
    if spot.rate - bump <= 0:
        raise PricingError("FX spot bump would create a nonpositive quote")
    up_rate, down_rate = spot.rate + bump, spot.rate - bump
    if up_rate == spot.rate or down_rate == spot.rate:
        raise PricingError("FX spot bump is smaller than binary64 resolution")
    contexts = tuple(
        replace(
            context,
            snapshot=context.snapshot.with_fx_rate(
                base_currency,
                quote_currency,
                rate,
                version=MarketSnapshotVersion(
                    "bump-" + content_hash((context.snapshot.snapshot_hash, rate))
                ),
            ),
        )
        for rate in (up_rate, down_rate)
    )
    engine = DiscountingEngine()
    base, up, down = (
        engine.price(instrument, context),
        engine.price(instrument, contexts[0]),
        engine.price(instrument, contexts[1]),
    )
    return FxDelta(base, up, down, bump, _derivative(up, down, bump))
