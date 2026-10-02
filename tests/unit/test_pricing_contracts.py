import io
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from parallax_risk.application.config import Settings
from parallax_risk.application.context import create_run_context
from parallax_risk.application.pricing import PricingService
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import (
    DomainValidationError,
    MissingMarketDataError,
    NumericalError,
    PricingError,
)
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.instruments.cashflows import (
    AccrualPeriod,
    CashFlow,
    FixedRateCashFlow,
    FloatingRateCashFlow,
    validate_schedule,
)
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    SwapDirection,
    ZeroCouponBond,
)
from parallax_risk.domain.market.curves.term_structures import CurveSet
from parallax_risk.domain.pricing._numbers import money_value, product, total
from parallax_risk.domain.pricing.engine import DiscountingEngine, PricingContext, forward_fx_rate
from parallax_risk.domain.pricing.sensitivities import fx_delta, parallel_rate_sensitivity
from tests.fixtures.deterministic import (
    INDEX,
    PERIODS,
    VALUATION,
    YEAR_ONE,
    YEAR_TWO,
    context,
    flat_curve,
    market,
    money,
)


def swap(**changes):
    contract = InterestRateSwap(
        money(),
        0.05,
        PERIODS,
        PERIODS,
        (VALUATION, YEAR_ONE),
        INDEX,
        DayCount.ACT_365_FIXED,
        DayCount.ACT_365_FIXED,
        SwapDirection.PAY_FIXED,
    )
    return replace(contract, **changes)


@pytest.mark.parametrize(
    "start,end,payment",
    [
        (VALUATION, VALUATION, YEAR_ONE),
        (YEAR_ONE, VALUATION, YEAR_TWO),
        (VALUATION, YEAR_ONE, VALUATION),
    ],
)
def test_invalid_accrual_bounds(start, end, payment):
    with pytest.raises(PricingError):
        AccrualPeriod(start, end, payment)


@pytest.mark.parametrize(
    "periods",
    [
        (),
        [],
        ("bad",),
        (PERIODS[0], AccrualPeriod(YEAR_ONE + timedelta(days=1), YEAR_TWO, YEAR_TWO)),
        (replace(PERIODS[0], payment_date=YEAR_TWO), PERIODS[1]),
    ],
)
def test_invalid_schedule(periods):
    with pytest.raises((DomainValidationError, NumericalError)):
        validate_schedule(periods, DayCount.ACT_365_FIXED)


@pytest.mark.parametrize(
    "change",
    [
        {"notional": money(-1)},
        {"notional": 100},
        {"fixed_rate": float("nan")},
        {"floating_spread": float("inf")},
        {"floating_gearing": True},
        {"direction": "pay_fixed"},
        {"index": ""},
        {"fixing_dates": (VALUATION,)},
        {"fixing_dates": [VALUATION, YEAR_ONE]},
        {"fixing_dates": (YEAR_ONE, YEAR_TWO)},
        {"fixed_periods": (PERIODS[0],)},
    ],
)
def test_swap_rejects_malformed_contract(change):
    with pytest.raises((DomainValidationError, NumericalError)):
        swap(**change)


@pytest.mark.parametrize(
    "change",
    [
        {"base_notional": money(-1, Currency.EUR)},
        {"base_notional": 1},
        {"quote_currency": Currency.EUR},
        {"quote_currency": "USD"},
        {"strike": 1.1},
        {"strike": Decimal("NaN")},
        {"strike": Decimal("0")},
        {"direction": "buy_base"},
    ],
)
def test_fx_contract_rejects_malformed_inputs(change):
    good = FxForward(
        money(100, Currency.EUR), Currency.USD, Decimal("1.1"), YEAR_ONE, FxDirection.BUY_BASE
    )
    with pytest.raises((DomainValidationError, NumericalError)):
        replace(good, **change)


def test_cashflow_type_validation_and_fixing_policy():
    with pytest.raises(PricingError):
        CashFlow(YEAR_ONE, 10)
    with pytest.raises(PricingError):
        FixedRateCashFlow(10, 0.1, PERIODS[0], DayCount.ACT_365_FIXED)
    with pytest.raises(PricingError):
        FloatingRateCashFlow(money(), "period", VALUATION, INDEX, DayCount.ACT_365_FIXED)
    with pytest.raises(PricingError):
        FloatingRateCashFlow(money(), PERIODS[0], YEAR_ONE, INDEX, DayCount.ACT_365_FIXED)
    with pytest.raises((DomainValidationError, NumericalError)):
        FixedRateBond(money(), float("inf"), PERIODS, DayCount.ACT_365_FIXED)
    with pytest.raises((DomainValidationError, NumericalError)):
        ZeroCouponBond(money(), datetime(2026, 1, 1))


def test_context_rejects_mismatch_and_bad_payment_policy():
    with pytest.raises(PricingError):
        PricingContext("snapshot", context().curves)
    with pytest.raises(PricingError):
        replace(context(), include_valuation_date_payments=1)
    with pytest.raises(PricingError):
        replace(context(), curves=CurveSet((replace(flat_curve(), valuation_date=YEAR_ONE),)))
    with pytest.raises(PricingError):
        replace(context(), curves=CurveSet((flat_curve(Currency.GBP),)))


def test_engine_rejects_unsupported_or_missing_reporting_currency():
    engine = DiscountingEngine()
    with pytest.raises(PricingError):
        engine.price(object(), context())
    with pytest.raises(PricingError):
        engine.price(ZeroCouponBond(money(), YEAR_ONE), "context")
    with pytest.raises(PricingError, match="reporting currency"):
        engine.price(CashFlow(VALUATION, money(1, Currency.GBP)), context())


def test_fx_maturity_cannot_precede_settled_spot():
    ctx = context(snapshot=market(value_date=VALUATION + timedelta(days=2)))
    with pytest.raises(PricingError):
        forward_fx_rate(Currency.EUR, Currency.USD, VALUATION + timedelta(days=1), ctx)
    with pytest.raises(PricingError):
        DiscountingEngine().price(
            FxForward(
                money(1, Currency.EUR),
                Currency.USD,
                Decimal("1.1"),
                VALUATION + timedelta(days=1),
                FxDirection.BUY_BASE,
            ),
            ctx,
        )


@pytest.mark.parametrize("bump", [0, -1, True, float("nan"), float("inf"), 1e-300])
def test_rate_bumps_reject_invalid_or_unresolvable_size(bump):
    with pytest.raises((DomainValidationError, NumericalError)):
        parallel_rate_sensitivity(
            ZeroCouponBond(money(), YEAR_ONE),
            context(),
            curve_ids=(flat_curve().curve_id,),
            bump_size=bump,
        )


@pytest.mark.parametrize("bump", [0, -1, 2, 1e-300, float("inf")])
def test_fx_bumps_reject_invalid_or_unresolvable_size(bump):
    contract = FxForward(
        money(1, Currency.EUR), Currency.USD, Decimal("1.1"), YEAR_ONE, FxDirection.BUY_BASE
    )
    with pytest.raises((DomainValidationError, NumericalError)):
        fx_delta(contract, context(), bump_size=bump)
    with pytest.raises(PricingError):
        fx_delta(ZeroCouponBond(money(), YEAR_ONE), context(), bump_size=1e-4)


@pytest.mark.parametrize("value", ["1e1000", "1e-1000"])
def test_money_float_conversion_rejects_range_loss(value):
    with pytest.raises(NumericalError):
        money_value(money(value))


@pytest.mark.parametrize("values", [(1e308, 1e308), (1e-300, 1e-300), (float("inf"), 0)])
def test_product_rejects_numerical_range_failure(values):
    with pytest.raises(NumericalError):
        product(*values)


@pytest.mark.parametrize("values", [(1e308, 1e308), (float("inf"), -float("inf")), (float("nan"),)])
def test_aggregation_rejects_nonfinite(values):
    with pytest.raises(NumericalError):
        total(values)


def test_pricing_evidence_rejects_inconsistent_results():
    result = DiscountingEngine().price(ZeroCouponBond(money(), YEAR_ONE), context())
    component = result.cashflows[0]
    for change in (
        {"amount": 1},
        {"discount_factor": 0},
        {"conversion_rate": -1},
        {"discount_curve_id": "id"},
        {"rate_origin": "redemption"},
        {"coupon_rate": float("nan")},
        {"present_value": 1},
    ):
        with pytest.raises((DomainValidationError, NumericalError)):
            replace(component, **change)
    for change in (
        {"npv": 1},
        {"model_version": "version"},
        {"assumptions": ()},
        {"market_snapshot_hash": "x"},
        {"curve_set_hash": "G" * 64},
        {"instrument_hash": 123},
        {"cashflows": (replace(component, present_value=money(1, Currency.EUR)),)},
    ):
        with pytest.raises((DomainValidationError, NumericalError)):
            replace(result, **change)


def test_pricing_service_correlates_logs_and_propagates_missing_fixing():
    stream = io.StringIO()
    service = PricingService(DiscountingEngine(), create_logger(stream=stream))
    run = create_run_context(
        Settings(), run_id=RiskRunId("pricing-test"), timestamp=datetime(2025, 1, 1, tzinfo=UTC)
    )
    priced = service.price(ZeroCouponBond(money(), YEAR_ONE), context(), run)
    assert priced.context is run
    assert priced.price.npv.amount > 0
    missing = context(snapshot=replace(market(), fixings=()))
    with pytest.raises(MissingMarketDataError):
        service.price(
            FloatingRateCashFlow(money(), PERIODS[0], VALUATION, INDEX, DayCount.ACT_365_FIXED),
            missing,
            run,
        )
    logs = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [item["event"] for item in logs] == [
        "pricing_started",
        "pricing_completed",
        "pricing_started",
        "pricing_failed",
    ]
    assert {item["run_id"] for item in logs} == {str(run.run_id)}
    assert logs[-1]["error_type"] == "MissingMarketDataError"
    assert all(
        set(item) <= {"event", "level", "timestamp", "run_id", "outcome", "error_type"}
        for item in logs
    )
