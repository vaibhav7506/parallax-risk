"""Replay the labelled Phase 2 synthetic fixture using production pricing code.

Run from the repository root with the installed Parallax Risk environment.
This example is not a production financial CLI or an observed-market result.
"""

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from parallax_risk.application.config import Settings
from parallax_risk.application.context import create_run_context
from parallax_risk.application.market_data import MarketSnapshotInput
from parallax_risk.application.pricing import PricingService
from parallax_risk.common.canonical import canonical_value
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import CurveId, QuoteId, RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.instruments.cashflows import AccrualPeriod
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    SwapDirection,
    ZeroCouponBond,
)
from parallax_risk.domain.market.curves.bootstrap import (
    DepositQuote,
    ParSwapQuote,
    bootstrap_discount_curve,
)
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import CurveSet, ForwardCurve, ZeroCurve
from parallax_risk.domain.pricing.engine import DiscountingEngine, PricingContext, forward_fx_rate
from parallax_risk.domain.pricing.sensitivities import fx_delta, parallel_rate_sensitivity

ROOT = Path(__file__).resolve().parents[1]


def example() -> dict[str, object]:
    """Ingest the explicit sample and return repeatable metadata and computed results."""
    snapshot = MarketSnapshotInput.model_validate_json(
        (ROOT / "data/sample/phase2_market.json").read_text(encoding="utf-8")
    ).to_domain()
    discounts = []
    for currency in snapshot.currencies:
        observations = sorted(
            (rate for rate in snapshot.rates if rate.currency == currency),
            key=lambda rate: rate.maturity,
        )
        first = observations[0]
        zero = ZeroCurve(
            CurveId(f"{currency}-sample"),
            currency,
            snapshot.valuation_date,
            first.day_count,
            (
                0.0,
                *(
                    year_fraction(snapshot.valuation_date, item.maturity, first.day_count)
                    for item in observations
                ),
            ),
            (first.rate, *(item.rate for item in observations)),
            first.compounding,
            ExtrapolationPolicy.ERROR,
            first.periods_per_year,
        )
        discounts.append(
            zero.to_discount_curve(
                interpolation=InterpolationKind.LOG_LINEAR, extrapolation=ExtrapolationPolicy.ERROR
            )
        )
    usd = next(curve for curve in discounts if curve.currency == Currency.USD)
    index = "USD-SYNTH-1Y"
    context = PricingContext(snapshot, CurveSet(tuple(discounts), (ForwardCurve(index, usd),)))
    maturities = tuple(
        sorted(rate.maturity for rate in snapshot.rates if rate.currency == Currency.USD)
    )
    first, second = maturities
    periods = (
        AccrualPeriod(snapshot.valuation_date, first, first),
        AccrualPeriod(first, second, second),
    )
    run = create_run_context(
        Settings(),
        run_id=RiskRunId("phase2-synthetic-demo"),
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        seed=0,
    )
    service = PricingService(DiscountingEngine(), create_logger(stream=sys.stderr))
    notional = Money(Decimal("1000000"), Currency.USD)
    fx = FxForward(
        Money(Decimal("1000000"), Currency.EUR),
        Currency.USD,
        Decimal("1.1"),
        second,
        FxDirection.BUY_BASE,
    )
    instruments = {
        "zero_coupon_bond": ZeroCouponBond(notional, second),
        "fixed_rate_bond": FixedRateBond(notional, 0.05, periods, DayCount.ACT_365_FIXED),
        "pay_fixed_swap": InterestRateSwap(
            notional,
            0.05,
            periods,
            periods,
            (snapshot.valuation_date, first),
            index,
            DayCount.ACT_365_FIXED,
            DayCount.ACT_365_FIXED,
            SwapDirection.PAY_FIXED,
        ),
        "fx_forward": fx,
    }
    prices = {
        name: service.price(instrument, context, run).price
        for name, instrument in instruments.items()
    }
    bootstrap = bootstrap_discount_curve(
        (
            DepositQuote(
                QuoteId("sample-deposit"), Currency.USD, first, 0.05, DayCount.ACT_365_FIXED
            ),
            ParSwapQuote(
                QuoteId("sample-par-swap"),
                Currency.USD,
                (first, second),
                0.05,
                DayCount.ACT_365_FIXED,
            ),
        ),
        curve_id=CurveId("USD-bootstrap"),
        currency=Currency.USD,
        valuation_date=snapshot.valuation_date,
        curve_day_count=DayCount.ACT_365_FIXED,
        interpolation=InterpolationKind.LOG_LINEAR,
        extrapolation=ExtrapolationPolicy.ERROR,
    )
    rate_risk = parallel_rate_sensitivity(
        instruments["zero_coupon_bond"], context, curve_ids=(usd.curve_id,), bump_size=1e-4
    )
    delta = fx_delta(fx, context, bump_size=1e-4)
    return {
        "project": "Parallax Risk",
        "phase": 2,
        "data_status": "SYNTHETIC SAMPLE: not observed market data",
        "run": run.as_metadata(),
        "snapshot_hash": snapshot.snapshot_hash,
        "curve_set_hash": context.curves.curve_hash,
        "prices": canonical_value(prices),
        "bootstrap": canonical_value(bootstrap),
        "bond_pv01": canonical_value(rate_risk.pv01),
        "bond_dv01": canonical_value(rate_risk.dv01),
        "fx_delta_per_spot_unit": delta.derivative_per_spot_unit,
        "fx_par_strike": forward_fx_rate(Currency.EUR, Currency.USD, second, context),
    }


if __name__ == "__main__":
    print(json.dumps(example(), sort_keys=True, indent=2))
