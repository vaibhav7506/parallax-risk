"""Independent high-precision and hand-derived formula benchmarks, in currency units."""

import math
from dataclasses import replace
from datetime import date
from decimal import Context, Decimal, localcontext

import pytest

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import CurveId
from parallax_risk.domain.instruments.cashflows import (
    AccrualPeriod,
    CashFlow,
    FixedRateCashFlow,
    FloatingRateCashFlow,
)
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    SwapDirection,
    ZeroCouponBond,
)
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import CurveSet, DiscountCurve, ForwardCurve
from parallax_risk.domain.pricing.engine import DiscountingEngine, PricingContext, forward_fx_rate
from parallax_risk.domain.pricing.results import RateOrigin
from parallax_risk.domain.pricing.sensitivities import fx_delta, parallel_rate_sensitivity
from tests.fixtures.deterministic import (
    INDEX,
    PERIODS,
    VALUATION,
    YEAR_ONE,
    YEAR_TWO,
    context,
    market,
    money,
)


def decimal_exp(value):
    with localcontext(Context(prec=50)):
        return Decimal(value).exp()


def value(instrument, ctx):
    return float(DiscountingEngine().price(instrument, ctx).npv.amount)


def swap(*, fixed_rate=0.05, notional="1000000", direction=SwapDirection.PAY_FIXED):
    return InterestRateSwap(
        money(notional),
        fixed_rate,
        PERIODS,
        PERIODS,
        (VALUATION, YEAR_ONE),
        INDEX,
        DayCount.ACT_365_FIXED,
        DayCount.ACT_365_FIXED,
        direction,
    )


def test_zero_coupon_and_signed_payment_against_decimal_exponential():
    ctx = context()
    expected = float(Decimal(100) * decimal_exp("-0.05"))
    assert value(ZeroCouponBond(money(), YEAR_ONE), ctx) == pytest.approx(
        expected, rel=1e-12, abs=1e-10
    )
    assert value(CashFlow(YEAR_ONE, money("-100")), ctx) == pytest.approx(
        -expected, rel=1e-12, abs=1e-10
    )
    assert value(ZeroCouponBond(money("0"), YEAR_TWO), ctx) == 0
    assert value(ZeroCouponBond(money(), YEAR_TWO), context(discount_rate=-0.01)) == pytest.approx(
        float(Decimal(100) * decimal_exp("0.02")), rel=1e-12, abs=1e-10
    )


def test_fixed_coupon_matches_declared_act360_accrual():
    coupon = FixedRateCashFlow(money("1000000"), 0.05, PERIODS[0], DayCount.ACT_360)
    expected = float(
        Decimal(1_000_000) * Decimal("0.05") * Decimal(365) / Decimal(360) * decimal_exp("-0.05")
    )
    result = DiscountingEngine().price(coupon, context())
    assert float(result.npv.amount) == pytest.approx(expected, rel=1e-12, abs=1e-8)
    assert result.cashflows[0].coupon_rate == 0.05
    assert result.cashflows[0].rate_origin == RateOrigin.FIXED_COUPON


def test_fixed_rate_par_bond_reconciles_coupons_and_redemption():
    curve = DiscountCurve(
        CurveId("simple-par"),
        Currency.USD,
        VALUATION,
        DayCount.ACT_365_FIXED,
        (0, 1, 2),
        (1, 1 / 1.05, 1 / 1.05**2),
        InterpolationKind.LOG_LINEAR,
        ExtrapolationPolicy.ERROR,
    )
    ctx = PricingContext(market(), CurveSet((curve,)))
    bond = FixedRateBond(money(), 0.05, PERIODS, DayCount.ACT_365_FIXED)
    result = DiscountingEngine().price(bond, ctx)
    assert float(result.npv.amount) == pytest.approx(100, rel=1e-12, abs=1e-10)
    assert [item.amount.amount for item in result.cashflows] == [
        Decimal(5),
        Decimal(5),
        Decimal(100),
    ]
    assert sum(float(item.present_value.amount) for item in result.cashflows) == pytest.approx(
        float(result.npv.amount), abs=1e-12
    )
    assert result.cashflows[-1].rate_origin == RateOrigin.REDEMPTION
    assert "dirty PV" in " ".join(result.assumptions)


def test_future_float_coupon_uses_separate_projection_and_discount_curves():
    coupon = FloatingRateCashFlow(
        money("1000000"),
        PERIODS[1],
        YEAR_ONE,
        INDEX,
        DayCount.ACT_365_FIXED,
        spread=0.001,
        gearing=1.5,
    )
    ctx = context(projection_rate=0.03)
    projected_rate = Decimal("1.5") * (decimal_exp("0.03") - 1) + Decimal("0.001")
    expected = float(Decimal(1_000_000) * projected_rate * decimal_exp("-0.10"))
    result = DiscountingEngine().price(coupon, ctx)
    assert float(result.npv.amount) == pytest.approx(expected, rel=1e-12, abs=1e-8)
    assert result.cashflows[0].rate_origin == RateOrigin.PROJECTED_FIXING
    assert result.cashflows[0].coupon_rate == pytest.approx(float(projected_rate), abs=1e-14)


def test_known_fixing_remains_fixed_even_when_projection_changes():
    coupon = FloatingRateCashFlow(money(), PERIODS[0], VALUATION, INDEX, DayCount.ACT_365_FIXED)
    ctx = context(snapshot=market(fixing_rate=0.07), projection_rate=0.03)
    result = DiscountingEngine().price(coupon, ctx)
    assert float(result.npv.amount) == pytest.approx(
        7 * float(decimal_exp("-.05")), rel=1e-12, abs=1e-10
    )
    assert result.cashflows[0].rate_origin == RateOrigin.HISTORICAL_FIXING
    assert result.cashflows[0].coupon_rate == 0.07


def test_single_curve_par_swap_zero_and_direction_symmetry():
    curve = DiscountCurve(
        CurveId("simple-par"),
        Currency.USD,
        VALUATION,
        DayCount.ACT_365_FIXED,
        (0, 1, 2),
        (1, 1 / 1.05, 1 / 1.05**2),
        InterpolationKind.LOG_LINEAR,
        ExtrapolationPolicy.ERROR,
    )
    ctx = PricingContext(
        market(fixing_rate=0.05), CurveSet((curve,), (ForwardCurve(INDEX, curve),))
    )
    par = swap()
    result = DiscountingEngine().price(par, ctx)
    assert float(result.npv.amount) == pytest.approx(0, abs=2e-9)
    assert len(result.cashflows) == 4
    off_par = replace(par, fixed_rate=0.06)
    pay = value(off_par, ctx)
    receive = value(replace(off_par, direction=SwapDirection.RECEIVE_FIXED), ctx)
    expected = -10_000 * (1 / 1.05 + 1 / 1.05**2)
    assert pay == pytest.approx(expected, rel=1e-12, abs=2e-9)
    assert receive == pytest.approx(-pay, abs=1e-12)


def test_dual_curve_par_swap_and_payment_lag():
    par_rate = float(decimal_exp("0.03") - 1)
    ctx = context(projection_rate=0.03, snapshot=market(fixing_rate=par_rate))
    assert value(swap(fixed_rate=par_rate), ctx) == pytest.approx(0, abs=2e-9)
    # A coupon payment lag affects discounting, while projection still uses accrual bounds.
    lagged = AccrualPeriod(YEAR_ONE, date(2026, 12, 29), YEAR_TWO)
    coupon = FloatingRateCashFlow(money(), lagged, YEAR_ONE, INDEX, DayCount.ACT_365_FIXED)
    accrued_years = Decimal((lagged.end - lagged.start).days) / Decimal(365)
    expected = float(
        Decimal(100) * (decimal_exp(str(Decimal(".03") * accrued_years)) - 1) * decimal_exp("-.1")
    )
    assert value(coupon, ctx) == pytest.approx(expected, rel=1e-12, abs=1e-10)


def test_fx_forward_formula_no_arbitrage_and_direction():
    ctx = context()
    forward = FxForward(
        money("1000000", Currency.EUR),
        Currency.USD,
        Decimal("1.12"),
        YEAR_TWO,
        FxDirection.BUY_BASE,
    )
    expected = float(
        Decimal(1_000_000)
        * (Decimal("1.1") * decimal_exp("-.06") - Decimal("1.12") * decimal_exp("-.10"))
    )
    result = DiscountingEngine().price(forward, ctx)
    assert float(result.npv.amount) == pytest.approx(expected, rel=1e-12, abs=1e-8)
    assert result.currency == Currency.USD
    assert result.cashflows[0].amount.currency == Currency.EUR
    assert result.cashflows[1].amount.currency == Currency.USD
    assert value(replace(forward, direction=FxDirection.SELL_BASE), ctx) == pytest.approx(
        -expected, rel=1e-12, abs=1e-8
    )
    fair = forward_fx_rate(Currency.EUR, Currency.USD, YEAR_TWO, ctx)
    assert fair == pytest.approx(float(Decimal("1.1") * decimal_exp(".04")), rel=1e-12, abs=1e-14)
    assert value(replace(forward, strike=Decimal(str(fair))), ctx) == pytest.approx(0, abs=1e-8)


def test_fx_forward_explicit_spot_settlement_lag_parity():
    settlement = date(2025, 1, 3)
    ctx = context(snapshot=market(value_date=settlement))
    forward = FxForward(
        money("1000000", Currency.EUR),
        Currency.USD,
        Decimal("1.12"),
        YEAR_ONE,
        FxDirection.BUY_BASE,
    )
    with localcontext(Context(prec=50)):
        settle_years = Decimal(2) / Decimal(365)
        immediate_spot = Decimal("1.1") * decimal_exp(str(-Decimal(".02") * settle_years))
        fair = immediate_spot * decimal_exp(".02")
        expected = Decimal(1_000_000) * (
            immediate_spot * decimal_exp("-.03") - Decimal("1.12") * decimal_exp("-.05")
        )
    assert forward_fx_rate(Currency.EUR, Currency.USD, YEAR_ONE, ctx) == pytest.approx(
        float(fair), rel=1e-12, abs=1e-14
    )
    assert value(forward, ctx) == pytest.approx(float(expected), rel=1e-12, abs=1e-8)
    assert value(replace(forward, strike=Decimal(str(float(fair)))), ctx) == pytest.approx(
        0, abs=1e-8
    )


def test_zero_knot_pv01_dv01_against_analytical_derivative_and_bump_stability():
    ctx = context()
    bond = ZeroCouponBond(money("1000000"), YEAR_TWO)
    target = (CurveId("USD-discount"),)
    result = parallel_rate_sensitivity(bond, ctx, curve_ids=target, bump_size=1e-5)
    expected_derivative = -2_000_000 * float(decimal_exp("-.1"))
    # Central derivative bias ~ (T*h)^2/6; 1e-9 relative allows this plus binary64 cancellation.
    assert result.derivative_per_unit_rate == pytest.approx(expected_derivative, rel=1e-9)
    assert float(result.pv01.amount) == pytest.approx(expected_derivative * 1e-4, rel=1e-9)
    assert result.dv01 == -result.pv01
    larger = parallel_rate_sensitivity(bond, ctx, curve_ids=target, bump_size=1e-4)
    assert larger.derivative_per_unit_rate == pytest.approx(expected_derivative, rel=1e-8)
    assert result.base.market_snapshot_hash == result.up.market_snapshot_hash
    assert result.base.curve_set_hash != result.up.curve_set_hash


def test_fx_delta_against_analytical_formula_with_settlement_lag():
    settlement = date(2025, 1, 3)
    ctx = context(snapshot=market(value_date=settlement))
    contract = FxForward(
        money("1000000", Currency.EUR),
        Currency.USD,
        Decimal("1.12"),
        YEAR_TWO,
        FxDirection.BUY_BASE,
    )
    result = fx_delta(contract, ctx, bump_size=1e-4)
    expected = (
        1_000_000
        * float(decimal_exp(str(-Decimal(".02") * Decimal(2) / Decimal(365))))
        * float(decimal_exp("-.06"))
    )
    assert result.derivative_per_spot_unit == pytest.approx(expected, rel=1e-10, abs=1e-5)
    assert result.base.curve_set_hash == result.up.curve_set_hash
    assert result.base.market_snapshot_hash != result.up.market_snapshot_hash
    assert ctx.snapshot.fx_spot(Currency.EUR, Currency.USD).rate == 1.1


def test_pricing_metadata_and_cashflow_reconciliation_are_reproducible():
    contract = FixedRateBond(money("1000000"), 0.05, PERIODS, DayCount.ACT_365_FIXED)
    ctx = context()
    result = DiscountingEngine().price(contract, ctx)
    assert DiscountingEngine().price(contract, ctx) == result
    assert result.valuation_date == VALUATION
    assert result.currency == Currency.USD
    assert result.model_name == "deterministic-discounting"
    assert str(result.model_version) == "0.2.0"
    assert result.market_snapshot_hash == ctx.snapshot.snapshot_hash
    assert result.curve_set_hash == ctx.curves.curve_hash
    assert result.assumptions
    assert math.fsum(float(item.present_value.amount) for item in result.cashflows) == float(
        result.npv.amount
    )
