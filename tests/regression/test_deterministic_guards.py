"""Keep missing-fixing, settlement cutoff and explicit projection regressions visible."""

from dataclasses import replace
from datetime import date

import pytest

from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import MissingMarketDataError
from parallax_risk.domain.instruments.cashflows import AccrualPeriod, CashFlow, FloatingRateCashFlow
from parallax_risk.domain.instruments.rates.contracts import FixedRateBond
from parallax_risk.domain.market.curves.term_structures import CurveSet
from parallax_risk.domain.pricing.engine import DiscountingEngine
from tests.fixtures.deterministic import INDEX, PERIODS, VALUATION, YEAR_ONE, context, market, money


def test_fixing_on_valuation_date_must_be_observed_even_with_projection_available():
    ctx = context(snapshot=replace(market(), fixings=()))
    coupon = FloatingRateCashFlow(money(), PERIODS[0], VALUATION, INDEX, DayCount.ACT_365_FIXED)
    with pytest.raises(MissingMarketDataError, match="historical"):
        DiscountingEngine().price(coupon, ctx)


def test_future_fixing_does_not_fall_back_to_discount_curve():
    ctx = replace(context(), curves=CurveSet(context().curves.discount_curves))
    coupon = FloatingRateCashFlow(money(), PERIODS[1], YEAR_ONE, INDEX, DayCount.ACT_365_FIXED)
    with pytest.raises(MissingMarketDataError, match="projection"):
        DiscountingEngine().price(coupon, ctx)


def test_paid_coupon_needs_no_historical_fixing_or_projection():
    old = AccrualPeriod(date(2023, 1, 1), date(2024, 1, 1), date(2024, 1, 1))
    coupon = FloatingRateCashFlow(money(), old, old.start, INDEX, DayCount.ACT_365_FIXED)
    result = DiscountingEngine().price(coupon, context(snapshot=replace(market(), fixings=())))
    assert result.npv.amount == 0
    assert result.cashflows == ()


def test_same_day_cutoff_is_explicit_and_bond_redemption_is_excluded_after_payment():
    engine = DiscountingEngine()
    payment = CashFlow(VALUATION, money())
    assert engine.price(payment, context()).npv.amount == 0
    assert engine.price(payment, context(include_today=True)).npv.amount == 100
    old = AccrualPeriod(date(2023, 1, 1), date(2024, 1, 1), date(2024, 1, 1))
    bond = FixedRateBond(money(), 0.05, (old,), DayCount.ACT_365_FIXED)
    assert engine.price(bond, context()).cashflows == ()
