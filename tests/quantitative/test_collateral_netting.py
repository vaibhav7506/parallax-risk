"""Hand-derived legal netting, collateral and deterministic MPOR targets."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import localcontext

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError, MissingMarketDataError
from parallax_risk.common.identifiers import CollateralMovementId, CsaId, NettingSetId, TradeId
from parallax_risk.domain.market.curves.term_structures import CurveSet
from parallax_risk.domain.portfolio.collateral import (
    CollateralMovement,
    collateral_value,
    convert,
    margin_call,
    mpor_scenario,
    validate_account,
)
from parallax_risk.domain.portfolio.csa import CollateralDirection
from parallax_risk.domain.portfolio.netting import TradeValue, aggregate
from tests.fixtures.deterministic import VALUATION, context, market, money
from tests.fixtures.portfolio import account, csa, dated_market, netting


def movement(amount=100, day=0, lag=2, name="call"):
    call = VALUATION + timedelta(days=day)
    return CollateralMovement(
        CollateralMovementId(name), call, call + timedelta(days=lag), money(amount)
    )


@pytest.mark.parametrize(
    "value,expected",
    [(10, 0), (15, 0), (16, 6), (100, 90), (-20, 0), (-25, 0), (-26, -6), (-100, -80)],
)
def test_threshold_strict_mta_full_difference(value, expected):
    call = margin_call(money(value), csa(), account(), context())
    assert call.transfer == money(expected)
    assert call.settlement_date == VALUATION + timedelta(days=2)


@pytest.mark.parametrize(
    "direction,value,vm,ia",
    [
        (CollateralDirection.RECEIVE_ONLY, -100, 0, 7),
        (CollateralDirection.POST_ONLY, 100, 0, -7),
        (CollateralDirection.RECEIVE_ONLY, 100, 90, 7),
        (CollateralDirection.POST_ONLY, -100, -80, -7),
        (CollateralDirection.TWO_WAY, -100, -80, 7),
    ],
)
def test_direction_independent_amount(direction, value, vm, ia):
    agreement = csa(direction=direction, independent_amount=money(ia))
    call = margin_call(money(value), agreement, account(), context())
    assert call.variation_margin_target == money(vm)
    assert call.total_target == call.transfer == money(vm + ia)


def test_pending_not_exposure_and_not_called_twice_then_return():
    ledger = account(opening_balances=(money(10),)).append(movement(80))
    call = margin_call(money(100), csa(), ledger, context())
    assert call.settled_collateral == money(10)
    assert call.projected_collateral == money(90)
    assert call.transfer == money(0)
    assert ledger.balances(VALUATION + timedelta(days=2)) == (money(90),)
    # Pending returns also avoid duplicate calls; only settled cash offsets current risk.
    returned = ledger.append(movement(-70, day=2, name="return"))
    day2 = dated_market(context(discount_rate=0), VALUATION + timedelta(days=2))
    result = margin_call(money(30), csa(), returned, day2)
    assert result.settled_collateral == money(90) and result.projected_collateral == money(20)
    assert result.transfer == money(0)
    assert returned.balances(VALUATION) == ledger.balances(VALUATION)
    assert returned.account_hash != ledger.account_hash
    assert returned.balances(VALUATION + timedelta(days=4)) == (money(20),)
    assert account().movements == ()


def test_off_schedule_and_mta_uses_exact_decimal_absolute_value():
    agreement = csa(frequency_days=3)
    day1 = dated_market(context(discount_rate=0), VALUATION + timedelta(days=1))
    assert not margin_call(money(100), agreement, account(), day1).on_schedule
    assert margin_call(money(100), agreement, account(), day1).transfer == money(0)
    agreement = csa(
        receive_threshold=money(0),
        post_threshold=money(0),
        minimum_transfer_amount=money("1.23456"),
    )
    with localcontext() as ctx:
        ctx.prec = 3
        assert margin_call(money("-1.23457"), agreement, account(), context()).transfer == money(
            "-1.23457"
        )


def test_fx_haircut_and_explicit_settlement_adjustment():
    assert collateral_value((money(100, Currency.EUR),), csa(), context()) == money(88)
    assert collateral_value((money(-100, Currency.EUR),), csa(), context()) == money(-88)
    # Quote settles one year later: domestic .05, foreign .03, S(today)=1.1 exp(-.02).
    ctx = context(snapshot=market(value_date=date(2026, 1, 1)))
    value = convert(money(100, Currency.EUR), Currency.USD, ctx)
    import math

    assert float(value.amount) == pytest.approx(110 * math.exp(-0.02), rel=1e-14)
    with pytest.raises(MissingMarketDataError):
        convert(money(100), Currency.EUR, ctx)
    with pytest.raises(DomainValidationError):
        collateral_value((money(1, Currency.GBP),), csa(), ctx)
    with pytest.raises(DomainValidationError):
        collateral_value((money(1), money(2)), csa(), ctx)


def test_fx_underflow_rejected_and_zero_lag_settlement():
    ctx = context(snapshot=market(value_date=date(2026, 1, 1)))
    curves = tuple(
        replace(
            curve,
            times=(0.0, 1.0),
            discount_factors=(1.0, 1e-300 if curve.currency == Currency.USD else 1e300),
        )
        for curve in ctx.curves.discount_curves
    )
    ctx = replace(ctx, curves=CurveSet(curves))
    with pytest.raises(DomainValidationError):
        convert(money(1, Currency.EUR), Currency.USD, ctx)
    agreement = csa(settlement_lag_days=0, minimum_transfer_amount=money(0))
    ledger = account().append(movement(90, lag=0))
    call = margin_call(money(100), agreement, ledger, context())
    assert call.settled_collateral == call.projected_collateral == money(90)
    assert call.transfer == money(0)
    receive = csa(direction=CollateralDirection.RECEIVE_ONLY)
    returned = account(opening_balances=(money(30),)).append(movement(-30))
    validate_account(returned, receive, context())
    with pytest.raises(DomainValidationError):
        validate_account(
            account(opening_balances=(money(30),)).append(movement(-31)), receive, context()
        )


def test_legal_netting_and_signed_collateral():
    marks = (TradeValue(TradeId("receive"), money(100)), TradeValue(TradeId("pay"), money(-80)))
    result = aggregate(netting(), marks, context())
    assert (result.signed_value, result.no_netting_positive, result.no_netting_negative) == (
        money(20),
        money(100),
        money(80),
    )
    assert result.net_positive == money(20) and result.net_negative == money(0)
    gross = aggregate(netting(netting_enforceable=False), marks, context())
    assert gross.net_positive == gross.collateralized_positive == money(100)
    assert gross.net_negative == money(80)
    collateral = aggregate(
        netting(csa=csa()), marks, context(), account(opening_balances=(money(15),))
    )
    assert collateral.collateralized_positive == money(5)
    excess = aggregate(netting(csa=csa()), marks, context(), account(opening_balances=(money(30),)))
    assert excess.collateralized_negative == money(10)
    posted = aggregate(
        netting(csa=csa()), marks, context(), account(opening_balances=(money(-30),))
    )
    assert posted.collateralized_positive == money(50)


@given(
    st.integers(-10000, 10000),
    st.integers(-10000, 10000),
    st.integers(0, 10000),
    st.integers(0, 10000),
)
@settings(max_examples=80, deadline=None)
def test_netting_bound_and_received_collateral_monotonicity(a, b, c, increment):
    marks = (TradeValue(TradeId("receive"), money(a)), TradeValue(TradeId("pay"), money(b)))
    raw = aggregate(netting(), marks, context())
    first = aggregate(netting(csa=csa()), marks, context(), account(opening_balances=(money(c),)))
    more = aggregate(
        netting(csa=csa()), marks, context(), account(opening_balances=(money(c + increment),))
    )
    assert raw.net_positive.amount <= raw.no_netting_positive.amount
    assert more.collateralized_positive.amount <= first.collateralized_positive.amount


@pytest.mark.parametrize("mpor", [0, 2, 10])
def test_mpor_frozen_physical_settled_balances(mpor):
    agreement = csa(margin_period_of_risk_days=mpor)
    ledger = account(opening_balances=(money(10),)).append(movement(80))
    endpoint = VALUATION + timedelta(days=mpor)
    scenario = mpor_scenario(
        money(150), agreement, ledger, VALUATION, dated_market(context(discount_rate=0), endpoint)
    )
    assert scenario.frozen_balances == (money(10),)
    assert scenario.positive_exposure == money(140)
    assert scenario.closeout_date == endpoint
    if mpor >= 2:
        assert ledger.balances(endpoint) == (money(90),)
    negative = mpor_scenario(
        money(0), agreement, ledger, VALUATION, dated_market(context(discount_rate=0), endpoint)
    )
    assert negative.positive_exposure == money(0)


def test_mpor_retains_fx_risk_and_rejects_wrong_endpoint():
    ledger = account(opening_balances=(money(100, Currency.EUR),))
    endpoint = VALUATION + timedelta(days=10)
    ctx = dated_market(context(discount_rate=0), endpoint)
    ctx = replace(
        ctx, snapshot=replace(ctx.snapshot, fx_spots=(replace(ctx.snapshot.fx_spots[0], rate=1.5),))
    )
    scenario = mpor_scenario(money(150), csa(), ledger, VALUATION, ctx)
    assert scenario.collateral_at_closeout == money(120)
    assert scenario.positive_exposure == money(30)
    with pytest.raises(DomainValidationError):
        mpor_scenario(money(100), csa(), ledger, VALUATION, context())
    with pytest.raises(DomainValidationError):
        mpor_scenario(money(100, Currency.EUR), csa(), ledger, VALUATION, ctx)


def test_ledger_and_aggregation_reject_bad_inputs():
    for changes in [
        {"account_id": "bad"},
        {"csa_id": "bad"},
        {"netting_set_id": "bad"},
        {"opening_balances": (money(1), money(2))},
        {"movements": (movement(), movement())},
        {"movements": (movement(day=-1),)},
    ]:
        with pytest.raises(DomainValidationError):
            account(**changes)
    for args in [
        ("id", VALUATION, VALUATION, money(1)),
        (CollateralMovementId("id"), VALUATION, VALUATION - timedelta(days=1), money(1)),
        (CollateralMovementId("id"), VALUATION, VALUATION, money(0)),
    ]:
        with pytest.raises(DomainValidationError):
            CollateralMovement(*args)
    with pytest.raises(DomainValidationError):
        account().append(None)
    with pytest.raises(DomainValidationError):
        account().balances(VALUATION - timedelta(days=1))
    with pytest.raises(DomainValidationError):
        account().balances(VALUATION, include_pending=1)
    invalid = [
        account(csa_id=CsaId("other")),
        account(movements=(movement(lag=1),)),
        account(movements=(movement(day=1),)),
    ]
    for ledger in invalid:
        with pytest.raises(DomainValidationError):
            validate_account(ledger, csa(frequency_days=3), context())
    with pytest.raises(DomainValidationError):
        validate_account(
            account(opening_balances=(money(-1),)),
            csa(direction=CollateralDirection.RECEIVE_ONLY),
            context(),
        )
    with pytest.raises(DomainValidationError):
        validate_account(
            account(opening_balances=(money(1),)),
            csa(direction=CollateralDirection.POST_ONLY),
            context(),
        )
    with pytest.raises(DomainValidationError):
        validate_account(None, csa(), context())
    with pytest.raises(DomainValidationError):
        collateral_value((), None, context())
    with pytest.raises(DomainValidationError):
        convert(None, Currency.USD, context())
    for mark in [TradeValue(TradeId("receive"), money(1))]:
        with pytest.raises(DomainValidationError):
            aggregate(netting(), (mark,), context())
        with pytest.raises(DomainValidationError):
            aggregate(netting(), (mark, mark), context())
    with pytest.raises(DomainValidationError):
        TradeValue("id", money(1))
    marks = (TradeValue(TradeId("receive"), money(100)), TradeValue(TradeId("pay"), money(-80)))
    for scope, ledger in [
        (netting(), account()),
        (netting(csa=csa()), None),
        (netting(csa=csa()), account(netting_set_id=NettingSetId("other"))),
    ]:
        with pytest.raises(DomainValidationError):
            aggregate(scope, marks, context(), ledger)
    with pytest.raises(DomainValidationError):
        aggregate(None, marks, context())
    with pytest.raises(DomainValidationError):
        aggregate(netting(), (replace(marks[0], value=money(1, Currency.EUR)), marks[1]), context())
