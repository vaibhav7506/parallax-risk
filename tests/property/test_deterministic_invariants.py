import math
from dataclasses import replace
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from parallax_risk.common.enums import Currency
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import ZeroCouponBond
from parallax_risk.domain.pricing.engine import DiscountingEngine, forward_fx_rate
from tests.fixtures.deterministic import YEAR_ONE, context, flat_curve, money


@given(
    rate=st.floats(min_value=-0.2, max_value=0.5, allow_nan=False),
    time=st.floats(min_value=0, max_value=2, allow_nan=False),
)
def test_flat_continuous_curve_matches_formula_and_is_positive(rate, time):
    df = flat_curve(rate=rate).discount(time)
    assert df > 0
    assert df == pytest.approx(math.exp(-rate * time), rel=3e-15, abs=3e-15)


@given(
    rate=st.floats(min_value=0, max_value=0.5, allow_nan=False),
    first=st.floats(min_value=0, max_value=1, allow_nan=False),
    gap=st.floats(min_value=0, max_value=1, allow_nan=False),
)
def test_monotonic_discounts_only_under_nonnegative_flat_rate_assumption(rate, first, gap):
    curve = flat_curve(rate=rate)
    assert curve.discount(first) >= curve.discount(first + gap)


@given(
    amount=st.integers(min_value=1, max_value=1_000_000),
    scale=st.integers(min_value=1, max_value=100),
    rate=st.floats(min_value=-0.1, max_value=0.2, allow_nan=False),
)
def test_bond_price_scales_linearly_in_notional(amount, scale, rate):
    engine, ctx = DiscountingEngine(), context(discount_rate=rate)
    base = engine.price(ZeroCouponBond(money(amount), YEAR_ONE), ctx)
    scaled = engine.price(ZeroCouponBond(money(amount * scale), YEAR_ONE), ctx)
    assert float(scaled.npv.amount) == pytest.approx(float(base.npv.amount) * scale, rel=2e-15)


@given(
    amount=st.integers(min_value=0, max_value=1_000_000),
    strike=st.floats(min_value=0.5, max_value=2, allow_nan=False),
)
def test_fx_direction_reversal_and_par_strike(amount, strike):
    ctx, engine = context(), DiscountingEngine()
    buy = FxForward(
        money(amount, Currency.EUR),
        Currency.USD,
        Decimal(str(strike)),
        YEAR_ONE,
        FxDirection.BUY_BASE,
    )
    sell = replace(buy, direction=FxDirection.SELL_BASE)
    assert engine.price(buy, ctx).npv == -engine.price(sell, ctx).npv
    par = replace(
        buy, strike=Decimal(str(forward_fx_rate(Currency.EUR, Currency.USD, YEAR_ONE, ctx)))
    )
    assert abs(float(engine.price(par, ctx).npv.amount)) <= max(1e-12, amount * 5e-16)
