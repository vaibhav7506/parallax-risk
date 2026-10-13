"""Independent closed-form targets, legal offsets, collateral and effective EE conventions."""

import math
from dataclasses import replace
from decimal import Decimal

import pytest

from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import TradeId
from parallax_risk.domain.ccr.challenger import challenger
from parallax_risk.domain.ccr.comparison import compare
from parallax_risk.domain.ccr.contracts import AssetClass
from parallax_risk.domain.ccr.standardized import standardized
from tests.fixtures.ccr import (
    empirical,
    inputs,
    margin,
    parameters,
    policy,
    risk_trade,
    service,
    workflow_inputs,
)
from tests.fixtures.deterministic import money


def amount(value):
    return float(value.amount)


def test_single_at_money_fx_closed_form_and_capital():
    result = standardized(inputs(), parameters())
    assert result.replacement_cost == money(0)
    assert result.aggregate_add_on == money(4)
    assert result.multiplier == 1
    assert amount(result.ead) == pytest.approx(5.6, rel=0, abs=1e-14)
    internal = challenger("cp/set", empirical((0.0, 2.0, 4.0)), 1, 1.4)
    report = compare(result, internal, policy(risk_weight=0.5))
    assert amount(internal.ead) == pytest.approx(4.9, rel=0, abs=1e-14)
    assert amount(report.standardized_capital.illustrative_rwa) == pytest.approx(
        2.8, rel=0, abs=1e-14
    )
    assert amount(report.capital_difference) == pytest.approx(-0.028, rel=0, abs=1e-14)
    assert abs(report.bridge_residual.amount) <= Decimal("1e-14")
    assert not report.exception


@pytest.mark.parametrize("maturity,expected", [(0.001, 0.2), (0.25, 0.5), (1, 1), (10, 1)])
def test_maturity_factor_floor_and_one_year_cap(maturity, expected):
    result = standardized(inputs(trades=(risk_trade(maturity=maturity),)), parameters())
    assert result.trade_contributions[0].maturity_factor == expected


@pytest.mark.parametrize(
    "start,end,bucket", [(0, 0.001, 1), (0, 0.5, 1), (0, 1, 2), (0, 5, 2), (5, 15, 3)]
)
def test_supervisory_duration_floor_and_buckets(start, end, bucket):
    trade = risk_trade(
        asset_class=AssetClass.INTEREST_RATE,
        currencies=(Currency.USD,),
        start=start,
        end=end,
        maturity=end,
    )
    result = standardized(inputs(trades=(trade,)), parameters())
    expected_duration = max((math.exp(-0.05 * start) - math.exp(-0.05 * end)) / 0.05, 0.04)
    assert result.trade_contributions[0].adjusted_notional == pytest.approx(
        100 * expected_duration, rel=0, abs=2e-12
    )
    assert result.trade_contributions[0].bucket == bucket


def test_offsets_within_pair_and_bucket_only_and_fx_orientation():
    long = risk_trade()
    short = replace(long, trade_id=TradeId("offset"), delta=-1)
    assert standardized(inputs(trades=(long, short)), parameters()).ead == money(0)
    inverse = replace(short, currencies=(Currency.USD, Currency.EUR), delta=1)
    assert standardized(inputs(trades=(long, inverse)), parameters()).ead == money(0)
    other_pair = replace(short, currencies=(Currency.GBP, Currency.USD))
    assert amount(
        standardized(inputs(trades=(long, other_pair)), parameters()).ead
    ) == pytest.approx(11.2, rel=0, abs=1e-14)
    ir = replace(
        long,
        trade_id=TradeId("long-ir"),
        asset_class=AssetClass.INTEREST_RATE,
        currencies=(Currency.USD,),
        maturity=6,
        end=6,
    )
    first_bucket = replace(ir, trade_id=TradeId("short-ir"), end=0.5, delta=-1)
    result = standardized(inputs(trades=(ir, first_bucket, long)), parameters())
    assert len(result.add_on_contributions) == 3
    assert amount(result.aggregate_add_on) == pytest.approx(
        sum(c.add_on for c in result.add_on_contributions), rel=0, abs=1e-14
    )


@pytest.mark.parametrize(
    "value,collateral,threshold,mta,nica,target",
    [
        (80e6, 90e6, 0, 1e6, 10e6, 0),
        (80e6, 79.5e6, 0, 1e6, 0, 1e6),
        (-10, -20, 0, 0, 0, 10),
        (0, 0, 10, 5, -2, 17),
    ],
)
def test_replacement_cost_cre99_examples_and_signed_nica(
    value, collateral, threshold, mta, nica, target
):
    terms = margin(
        threshold=money(threshold),
        minimum_transfer_amount=money(mta),
        net_independent_collateral=money(nica),
    )
    result = standardized(
        inputs(value=money(value), collateral=money(collateral), margin=terms), parameters()
    )
    assert result.replacement_cost == money(target)


def test_multiplier_formula_floor_and_excess_collateral():
    base = standardized(inputs(value=money(-1)), parameters())
    target = 0.05 + 0.95 * math.exp(-1 / 7.6)
    assert base.multiplier == pytest.approx(target, rel=0, abs=1e-15)
    assert base.replacement_cost == money(0)
    held = standardized(inputs(collateral=money(1)), parameters())
    assert held.ead == base.ead
    floor = standardized(inputs(value=money(-100000)), parameters())
    assert floor.multiplier == 0.05
    assert amount(floor.ead) == pytest.approx(0.28, rel=0, abs=1e-14)
    zero = standardized(
        inputs(value=money(10), trades=(risk_trade(notional=money(0)),)), parameters()
    )
    assert zero.multiplier == 1 and zero.potential_future_exposure == money(0)
    assert zero.ead == money(14)


def test_margin_factor_and_binding_unmargined_cap_bridge():
    short = risk_trade(maturity=0.001)
    result = standardized(
        inputs(trades=(short,), margin=margin(threshold=money(1000))), parameters()
    )
    assert result.trade_contributions[0].maturity_factor == pytest.approx(0.3, rel=0, abs=1e-15)
    assert result.uncapped_ead.amount > result.ead.amount
    assert result.ead == result.unmargined_ead_cap
    internal = challenger("cp/set", empirical((0.0, 0.0, 0.0)), 1, 1.4)
    report = compare(result, internal, policy())
    assert abs(report.bridge_residual.amount) <= Decimal("1e-12")
    assert report.component_bridge[-1][1].amount > 0


@pytest.mark.parametrize("scale", [0.1, 2, 1000])
def test_positive_homogeneity_with_collateral_threshold_and_nica(scale):
    source = inputs(
        value=money(3),
        collateral=money(5),
        margin=margin(
            threshold=money(2),
            minimum_transfer_amount=money(1),
            net_independent_collateral=money(1),
        ),
    )
    factor = Decimal(str(scale))
    scaled = replace(
        source,
        value=source.value.scale(factor),
        collateral=source.collateral.scale(factor),
        trades=tuple(replace(t, notional=t.notional.scale(factor)) for t in source.trades),
        margin=replace(
            source.margin,
            threshold=source.margin.threshold.scale(factor),
            minimum_transfer_amount=source.margin.minimum_transfer_amount.scale(factor),
            net_independent_collateral=source.margin.net_independent_collateral.scale(factor),
        ),
    )
    assert amount(standardized(scaled, parameters()).ead) == pytest.approx(
        scale * amount(standardized(source, parameters()).ead), rel=0, abs=1e-10
    )


def test_effective_ee_running_max_right_endpoint_short_horizon():
    result = challenger("cp/set", empirical(), 1, 1.4)
    assert result.effective_expected_exposure == (10, 20, 20)
    assert result.epe == money(8.75)
    assert result.effective_epe == money(20)
    assert result.ead == money(28)
    short = challenger("cp/set", empirical((10.0, 20.0, 5.0), (0.0, 0.1, 0.5)), 0.5, 2)
    assert short.epe == money(8) and short.effective_epe == money(20)
    assert short.ead == money(40)
    longer = challenger(
        "cp/set", empirical((10.0, 20.0, 5.0, 1000.0), (0.0, 0.25, 1.0, 2.0)), 2, 1.4
    )
    assert longer.ead == result.ead


def test_actual_deterministic_mc_exposure_closed_form_and_legal_netting():
    request, book, markets, run = workflow_inputs()
    components = tuple(
        replace(c, process=replace(c.process, volatility=0), initial_state=(1.2,))
        if c.name == "fx"
        else c
        for c in request.components
    )
    request = replace(request, components=components)
    markets = replace(markets, request=request)
    cp = book.counterparties[0]
    netting = cp.netting_sets[0]
    trade = netting.trades[0]
    offset = replace(trade, trade_id=TradeId("offset"), quantity=Decimal(-1))
    book = replace(
        book,
        counterparties=(replace(cp, netting_sets=(replace(netting, trades=(trade, offset)),)),),
    )
    netted = service().run(request, book, markets, run, parameters(), policy())
    assert netted.standardized_ead == money(0) and netted.challenger_ead == money(0)
    no_netting = replace(
        book,
        counterparties=(
            replace(
                cp,
                netting_sets=(replace(netting, trades=(trade, offset), netting_enforceable=False),),
            ),
        ),
    )
    gross = service().run(request, no_netting, markets, run, parameters(), policy())
    assert len(gross.scopes) == 2 and gross.standardized_ead.amount > 0
    long = next(
        r.comparison.challenger for r in gross.scopes if r.comparison.challenger.ead.amount > 0
    )
    for t, value in zip(long.times[:-1], long.expected_exposure[:-1], strict=True):
        assert value == pytest.approx(10 * math.exp(-0.03 * (1 - t)), rel=0, abs=2e-12)
    assert long.expected_exposure[-1] == 0
    assert long.effective_expected_exposure[-1] > 0
    assert len({r.unit_hash for r in gross.scopes}) == 2


@pytest.mark.parametrize(
    "absolute,relative,exception", [(1, 0.1, False), (0.5, 0.1, True), (0, 1, False)]
)
def test_exception_requires_both_strict_thresholds(absolute, relative, exception):
    sa = standardized(inputs(), parameters())
    imm = challenger("cp/set", empirical((0.0, 2.0, 4.0)), 1, 1.4)
    assert (
        compare(
            sa, imm, policy(absolute_tolerance=money(absolute), relative_tolerance=relative)
        ).exception
        is exception
    )


def test_zero_reference_ratio_is_undefined_not_infinite():
    sa = standardized(inputs(trades=(risk_trade(notional=money(0)),)), parameters())
    imm = challenger("cp/set", empirical(), 1, 1.4)
    report = compare(sa, imm, policy())
    assert report.relative_ead_difference is None and report.exception


def test_ir_within_bucket_offset_and_currency_separation():
    long = risk_trade(asset_class=AssetClass.INTEREST_RATE, currencies=(Currency.USD,), end=1)
    short = replace(long, trade_id=TradeId("short"), delta=-1)
    assert standardized(inputs(trades=(long, short)), parameters()).ead == money(0)
    foreign = replace(short, currencies=(Currency.EUR,))
    separate = standardized(inputs(trades=(long, foreign)), parameters())
    target = 2 * 100 * (1 - math.exp(-0.05)) / 0.05 * 0.005 * 1.4
    assert amount(separate.ead) == pytest.approx(target, rel=0, abs=1e-12)


def test_exception_equality_at_each_boundary_does_not_trigger():
    sa = standardized(
        inputs(value=money(10), trades=(risk_trade(notional=money(0)),)), parameters()
    )
    imm = challenger("cp/set", empirical((20.0, 20.0, 20.0)), 1, 1.4)
    assert sa.ead == money(14) and imm.ead == money(28)
    assert not compare(
        sa, imm, policy(absolute_tolerance=money(14), relative_tolerance=0)
    ).exception
    assert not compare(sa, imm, policy(absolute_tolerance=money(0), relative_tolerance=1)).exception


def test_actual_domestic_irs_mc_profile_has_independent_fixed_coupon_target():
    from parallax_risk.common.enums import DayCount
    from parallax_risk.domain.exposure.markets import RateBinding
    from parallax_risk.domain.instruments.cashflows import AccrualPeriod
    from parallax_risk.domain.instruments.rates.contracts import InterestRateSwap, SwapDirection
    from tests.fixtures.deterministic import INDEX, VALUATION, YEAR_ONE, market

    request, book, markets, run = workflow_inputs()
    period = AccrualPeriod(VALUATION, YEAR_ONE, YEAR_ONE)
    contract = InterestRateSwap(
        money(100),
        0.02,
        (period,),
        (period,),
        (VALUATION,),
        INDEX,
        DayCount.ACT_365_FIXED,
        DayCount.ACT_365_FIXED,
        SwapDirection.PAY_FIXED,
    )
    cp = book.counterparties[0]
    ns = cp.netting_sets[0]
    position = replace(ns.trades[0], instrument=contract)
    book = replace(
        book, counterparties=(replace(cp, netting_sets=(replace(ns, trades=(position,)),)),)
    )
    usd = next(r for r in markets.rates if r.currency == Currency.USD)
    markets = replace(
        markets,
        rates=(
            RateBinding(Currency.USD, usd.component, (INDEX,)),
            *(r for r in markets.rates if r.currency != Currency.USD),
        ),
        initial_fixings=market(fixing_rate=math.expm1(0.03)).fixings,
    )
    result = service().run(request, book, markets, run, parameters(), policy())
    profile = result.scopes[0].comparison.challenger
    coupon = 100 * (math.expm1(0.03) - 0.02)
    for time, ee in zip(profile.times[:-1], profile.expected_exposure[:-1], strict=True):
        assert ee == pytest.approx(coupon * math.exp(-0.03 * (1 - time)), rel=0, abs=1e-12)
    assert profile.expected_exposure[-1] == 0
    contribution = result.scopes[0].comparison.standardized.trade_contributions[0]
    assert contribution.effective_notional > 0
