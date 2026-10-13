"""Unsupported scope, units, finiteness and explicit assumptions reject without repair."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import ParallaxError
from parallax_risk.domain.ccr.challenger import challenger
from parallax_risk.domain.ccr.comparison import compare
from parallax_risk.domain.ccr.contracts import AssetClass
from parallax_risk.domain.ccr.mapping import map_trade
from parallax_risk.domain.ccr.standardized import standardized
from parallax_risk.domain.instruments.rates.contracts import InterestRateSwap, SwapDirection
from tests.fixtures.ccr import (
    empirical,
    inputs,
    margin,
    parameters,
    policy,
    risk_trade,
    workflow_inputs,
)
from tests.fixtures.deterministic import INDEX, PERIODS, VALUATION, context, market, money
from tests.fixtures.portfolio import trade


@pytest.mark.parametrize(
    "changes",
    [
        {"trade_id": "fx"},
        {"asset_class": "fx"},
        {"asset_class": AssetClass.CREDIT},
        {"asset_class": AssetClass.EQUITY},
        {"asset_class": AssetClass.COMMODITY},
        {"currencies": []},
        {"currencies": (Currency.USD,)},
        {"currencies": (Currency.USD, Currency.USD)},
        {"notional": 1},
        {"notional": money(-1)},
        {"delta": 0.5},
        {"delta": True},
        {"maturity": 0},
        {"maturity": float("inf")},
        {"start": -1},
        {"end": 1},
        {
            "asset_class": AssetClass.INTEREST_RATE,
            "currencies": (Currency.USD,),
            "start": 1,
            "end": 1,
        },
        {"asset_class": AssetClass.INTEREST_RATE, "currencies": (Currency.USD,), "end": 2},
    ],
)
def test_invalid_supervisory_trade(changes):
    with pytest.raises(ParallaxError):
        risk_trade(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"source": ""},
        {"alpha": 0},
        {"interest_rate_factor": -1},
        {"fx_factor": float("nan")},
        {"duration_decay": 0},
        {"multiplier_floor": 0},
        {"multiplier_floor": 1},
        {"business_days_per_year": True},
        {"minimum_horizon_business_days": 0},
        {"minimum_horizon_business_days": 251},
    ],
)
def test_invalid_supervisory_parameters(changes):
    with pytest.raises(ParallaxError):
        parameters(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"threshold": 0},
        {"threshold": money(-1)},
        {"minimum_transfer_amount": money(-1)},
        {"net_independent_collateral": money(0, Currency.EUR)},
        {"margin_period_business_days": 9},
        {"margin_period_business_days": True},
        {"source": ""},
    ],
)
def test_invalid_margin_terms(changes):
    with pytest.raises(ParallaxError):
        margin(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"scope": ""},
        {"value": 0},
        {"collateral": 0},
        {"trades": ()},
        {"trades": (risk_trade(), risk_trade())},
        {"margin": 0},
        {"collateral": money(0, Currency.EUR)},
        {
            "margin": margin(
                threshold=money(0, Currency.EUR),
                minimum_transfer_amount=money(0, Currency.EUR),
                net_independent_collateral=money(0, Currency.EUR),
            )
        },
    ],
)
def test_invalid_standardized_inputs(changes):
    with pytest.raises(ParallaxError):
        inputs(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "USD"},
        {"absolute_tolerance": 1},
        {"absolute_tolerance": money(-1)},
        {"absolute_tolerance": money(1, Currency.EUR)},
        {"relative_tolerance": -1},
        {"risk_weight": -1},
        {"capital_ratio": 1.1},
        {"challenger_alpha": 0},
        {"source": ""},
    ],
)
def test_invalid_comparison_policy(changes):
    with pytest.raises(ParallaxError):
        policy(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "USD"},
        {"times": (0, 0)},
        {"expected_exposure": (1,)},
        {"expected_exposure": [1, 2, 3]},
        {"expected_exposure": (0, -1, 0)},
        {"expected_exposure": (0, float("inf"), 0)},
        {"paths": 0},
        {"paths": True},
    ],
)
def test_invalid_empirical_profile(changes):
    with pytest.raises(ParallaxError):
        challenger("cp/set", replace(empirical(), **changes), 1, 1.4)


def test_invalid_types_horizon_and_comparison_scope():
    with pytest.raises(ParallaxError):
        standardized(None, parameters())
    with pytest.raises(ParallaxError):
        standardized(inputs(), None)
    with pytest.raises(ParallaxError):
        challenger("cp/set", None, 1, 1.4)
    with pytest.raises(ParallaxError):
        challenger("cp/set", empirical(), 0.5, 1.4)
    sa = standardized(inputs(), parameters())
    imm = challenger("cp/set", empirical(), 1, 1.4)
    with pytest.raises(ParallaxError):
        compare(None, imm, policy())
    with pytest.raises(ParallaxError):
        compare(sa, replace(imm, scope="other"), policy())
    with pytest.raises(ParallaxError):
        compare(sa, replace(imm, currency=Currency.EUR), policy())
    with pytest.raises(ParallaxError):
        compare(sa, replace(imm, alpha=2), policy())
    with pytest.raises(ParallaxError):
        compare(sa, replace(imm, ead=money(-1)), policy())
    with pytest.raises(ParallaxError):
        compare(sa, replace(imm, ead=money(1, Currency.EUR)), policy())


@pytest.mark.parametrize("value", ["1e400", "1e-400"])
def test_binary64_range_rejects_instead_of_erasing_notional(value):
    with pytest.raises(ParallaxError):
        standardized(inputs(trades=(risk_trade(notional=money(value)),)), parameters())


def test_overflow_aggregate_and_small_duration_numerics():
    with pytest.raises(ParallaxError):
        standardized(inputs(margin=margin()), parameters(minimum_horizon_business_days=20))
    with pytest.raises(ParallaxError):
        standardized(inputs(value=money("1e308")), parameters(alpha=10))
    short = risk_trade(
        asset_class=AssetClass.INTEREST_RATE, currencies=(Currency.USD,), start=0, end=1e-10
    )
    result = standardized(inputs(trades=(short,)), parameters())
    assert result.trade_contributions[0].adjusted_notional == 4


def swap(**changes):
    return replace(
        InterestRateSwap(
            money(100),
            0.05,
            PERIODS,
            PERIODS,
            (PERIODS[0].start, PERIODS[1].start),
            INDEX,
            DayCount.ACT_365_FIXED,
            DayCount.ACT_365_FIXED,
            SwapDirection.PAY_FIXED,
        ),
        **changes,
    )


@pytest.mark.parametrize(
    "direction,quantity,delta",
    [
        (SwapDirection.PAY_FIXED, 2, 1),
        (SwapDirection.RECEIVE_FIXED, 2, -1),
        (SwapDirection.PAY_FIXED, -2, -1),
        (SwapDirection.RECEIVE_FIXED, -2, 1),
    ],
)
def test_swap_mapping_sign_quantity_and_remaining_accrual(direction, quantity, delta):
    position = trade(instrument=swap(direction=direction), quantity=Decimal(quantity))
    mapped = map_trade(position, VALUATION, Currency.USD, context())
    assert mapped.notional == money(200) and mapped.delta == delta
    assert mapped.start == 0 and mapped.end == mapped.maturity == 2


@pytest.mark.parametrize(
    "changes",
    [{"floating_spread": 0.001}, {"floating_gearing": 2}, {"notional": money(100, Currency.EUR)}],
)
def test_reject_unsupported_swap_mapping(changes):
    with pytest.raises(ParallaxError):
        map_trade(trade(instrument=swap(**changes)), VALUATION, Currency.USD, context())


def test_fx_mapping_and_unsupported_contract_date_currency():
    _, book, _, _ = workflow_inputs()
    fx = book.counterparties[0].netting_sets[0].trades[0]
    mapped = map_trade(fx, VALUATION, Currency.USD, context())
    assert mapped.notional.amount == Decimal("110.00000000000001")
    assert mapped.asset_class == AssetClass.FX
    with pytest.raises(ParallaxError):
        map_trade(
            replace(
                fx, termination_date=VALUATION + timedelta(days=1), termination_reason="Synthetic"
            ),
            VALUATION,
            Currency.USD,
            context(),
        )
    from parallax_risk.domain.instruments.fx.contracts import FxDirection

    sold = replace(fx, instrument=replace(fx.instrument, direction=FxDirection.SELL_BASE))
    assert map_trade(sold, VALUATION, Currency.USD, context()).delta == -1
    with pytest.raises(ParallaxError):
        map_trade(None, VALUATION, Currency.USD, context())
    with pytest.raises(ParallaxError):
        map_trade(trade(), VALUATION, Currency.USD, context())
    with pytest.raises(ParallaxError):
        map_trade(fx, VALUATION + timedelta(days=1), Currency.USD, context())
    with pytest.raises(ParallaxError):
        map_trade(fx, VALUATION, Currency.EUR, context())
    with pytest.raises(ParallaxError):
        map_trade(
            fx,
            VALUATION,
            Currency.USD,
            context(snapshot=market(value_date=VALUATION + timedelta(days=2))),
        )
    with pytest.raises(ParallaxError):
        map_trade(replace(fx, quantity=Decimal("1e-400")), VALUATION, Currency.USD, context())
