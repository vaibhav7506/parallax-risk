"""Actual future repricing and path-local cash/fixing history with injected failures."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CounterpartyId, NettingSetId
from parallax_risk.domain.credit.dependence import ReducedFormSpread
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario, DependenceKind
from parallax_risk.domain.exposure.markets import FxBinding, RateBinding
from parallax_risk.domain.instruments.cashflows import AccrualPeriod, FloatingRateCashFlow
from parallax_risk.domain.market.observations import RateFixing
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.arrays import FrozenArray
from parallax_risk.domain.simulation.contracts import PathBatch
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import StreamKey
from tests.fixtures.deterministic import SOURCE, VALUATION, YEAR_ONE, money
from tests.fixtures.exposure import (
    collateral_book,
    fx_book,
    fx_markets,
    fx_request,
    markets,
    request,
    service,
)
from tests.fixtures.portfolio import account, netting, portfolio, run, trade


def test_future_fx_forward_ee_against_analytic_positive_part():
    from math import exp

    from parallax_risk.domain.simulation.analytics import gbm_call_expectation

    req = fx_request(paths=2048, batch=128)
    result = service().run(req, fx_book(), fx_markets(req), run())
    t = req.grid.times[-1]
    expected = (
        100 * exp(-0.03 * (1 - t)) * gbm_call_expectation(req.components[2].process, 1.1, t, 1.1)
    )
    samples = result.positive_paths.array[:, -1, 0]
    sem = samples.std(ddof=1) / np.sqrt(req.path_count)
    assert abs(result.total_profile.expected_exposure[-1] - expected) < 6 * sem
    assert result.total_profile.expected_exposure[0] == pytest.approx(0, abs=1e-12)


def test_synthetic_example_replay_and_credit_marginals():
    from parallax_risk.application.exposure_examples import example

    first = example(16)
    second = example(16)
    for a, b in zip(first, second, strict=True):
        assert a == b
        assert a.counterparties[0].scenario_survival[0] == 1
    assert len({r.market_path_digest for r in first}) == 1
    assert (
        first[0].counterparties[0].baseline_survival == first[1].counterparties[0].scenario_survival
    )


def credit(req, book=None, **changes):
    name = (book or portfolio()).counterparties[0].counterparty_id
    return replace(
        CreditScenario(
            name,
            PiecewiseHazardCurve((0.0, req.grid.times[-1]), (0.2,)),
            RecoveryAssumption(0.4),
            StreamKey(42, 1),
        ),
        **changes,
    )


def test_actual_conditional_pricing_legal_aggregation_and_batch_replay():
    req = request()
    book = portfolio()
    result = service().run(req, book, markets(req), run())
    assert result.positive_paths.shape == (8, 2, 1)
    assert result.negative_paths.shape == (8, 2, 1)
    for step, market in enumerate(
        markets(req).path(book, next(MonteCarloEngine().iter_batches(req)), 0)
    ):
        expected = DiscountingEngine().price(
            book.counterparties[0].netting_sets[0].trades[1].instrument, market
        ).npv.amount * Decimal(".2")
        assert result.positive_paths.array[0, step, 0] == pytest.approx(float(expected), rel=1e-14)
    second = replace(req, batch_size=8)
    replay = service().run(second, book, markets(second), run())
    np.testing.assert_array_equal(result.positive_paths.array, replay.positive_paths.array)
    assert result.market_path_digest == replay.market_path_digest
    assert len(result.market_scenario_hash) == 64
    assert result.counterparties[0].default_comparison is None
    disabled = replace(
        book,
        counterparties=(
            replace(book.counterparties[0], netting_sets=(netting(netting_enforceable=False),)),
        ),
    )
    gross = service().run(req, disabled, markets(req), run())
    assert np.all(gross.positive_paths.array >= result.positive_paths.array)
    assert np.all(gross.negative_paths.array > 0)


def test_zero_exposure_maturity_and_multiple_scope_no_cross_netting():
    req = request()
    cp = portfolio().counterparties[0]
    empty = portfolio(counterparties=(replace(cp, netting_sets=(netting(trades=()),)),))
    result = service().run(req, empty, markets(req), run(), credit=(credit(req),))
    assert result.total_profile.expected_positive_exposure == 0
    assert result.counterparties[0].default_comparison.ratio is None
    book = portfolio(
        counterparties=(
            replace(
                cp,
                netting_sets=(
                    netting(trades=(trade(),)),
                    netting(netting_set_id=NettingSetId("other"), trades=(trade("other", -100),)),
                ),
            ),
        )
    )
    result = service().run(req, book, markets(req), run())
    assert result.total_profile.expected_exposure == result.total_profile.expected_negative_exposure
    dates = (VALUATION, YEAR_ONE)
    req = request(dates=dates)
    matured = service().run(req, portfolio(), markets(req, dates), run())
    assert matured.total_profile.expected_exposure[-1] == 0


@pytest.mark.parametrize("lag", [0, 1, 2])
def test_path_local_daily_margin_settlement_and_no_duplicate_calls(lag):
    dates = tuple(VALUATION + timedelta(days=i) for i in range(4))
    req = request(paths=4, batch=2, dates=dates)
    book, ledger = collateral_book(lag)
    result = service().run(req, book, markets(req, dates), run(), accounts=(ledger,))
    assert ledger.movements == ()
    if lag == 0:
        assert np.all(result.positive_paths.array == 0)
    else:
        assert np.all(result.positive_paths.array[:, :lag, 0] > 90)
        assert np.all(result.positive_paths.array[:, lag:, 0] < 3)
    assert len(result.initial_account_hashes) == 1


def test_static_and_dynamic_credit_workflows_with_fixed_thresholds():
    req = fx_request()
    book = fx_book()
    cp = book.counterparties[0].counterparty_id
    baseline = credit(req, book)
    static = replace(baseline, kind=DependenceKind.STATIC_RANK, rho=0.8, rank_key=StreamKey(42, 2))
    a = service().run(req, book, fx_markets(req), run(), credit=(static,))
    comparison = a.counterparties[0].default_comparison
    assert comparison.baseline.defaults == comparison.scenario.defaults
    dynamic = replace(
        baseline,
        kind=DependenceKind.DYNAMIC_SPREAD,
        spread_component="credit",
        spread_policy=ReducedFormSpread(RecoveryAssumption(0.4)),
    )
    b = service().run(req, book, fx_markets(req), run(), credit=(dynamic,))
    assert b.counterparties[0].counterparty_id == cp
    assert b.counterparties[0].default_comparison.baseline == comparison.baseline
    # With constant intensity .12/.6=.2, dynamic and deterministic inversion agree.
    constant = fx_request(spread_vol=0)
    c = service().run(constant, book, fx_markets(constant), run(), credit=(dynamic,))
    assert c.counterparties[0].default_comparison.difference_in_default_weighted_exposure == 0


def test_correlated_market_credit_brownian_factors():
    req = fx_request(paths=5000, batch=5000)
    values = tuple(
        tuple(0.7 if {i, j} == {2, 3} else 1.0 if i == j else 0.0 for j in range(4))
        for i in range(4)
    )
    req = replace(req, correlation=CorrelationMatrix(req.factor_names, values))
    batch = next(MonteCarloEngine().iter_batches(req))
    log_fx = np.log(batch.values.array[:, 1, 2] / 1.1)
    log_spread = np.log(batch.values.array[:, 1, 3] / 0.12)
    assert np.corrcoef(log_fx, log_spread)[0, 1] == pytest.approx(0.7, abs=0.03)
    dates = (VALUATION, date(2025, 7, 1))
    small = replace(req, path_count=4, batch_size=4)
    result = service().run(
        small,
        fx_book(),
        fx_markets(small, dates),
        run(),
        credit=(
            credit(
                small,
                kind=DependenceKind.DYNAMIC_SPREAD,
                spread_component="credit",
                spread_policy=ReducedFormSpread(RecoveryAssumption(0.4)),
            ),
        ),
    )
    assert result.simulation.correlation_hash == req.correlation.hash


def test_future_fixings_generated_once_and_retained_without_lookahead():
    dates = (VALUATION, date(2025, 1, 2), date(2025, 1, 3))
    req = request(paths=1, batch=1, dates=dates)
    period = AccrualPeriod(dates[1], date(2025, 1, 5), date(2025, 1, 5))
    coupon = FloatingRateCashFlow(
        money(1000), period, dates[1], "USD-SYNTH-1Y", DayCount.ACT_365_FIXED
    )
    record = trade(instrument=coupon, effective_date=dates[1])
    cp = portfolio().counterparties[0]
    book = portfolio(counterparties=(replace(cp, netting_sets=(netting(trades=(record,)),)),))
    scenario = markets(req, dates, knot_dates=(dates[1], period.end, YEAR_ONE))
    batch = PathBatch(
        0, FrozenArray.from_array(np.array([[[0.03], [0.01], [0.5]]], dtype=np.float64)), 0
    )
    path = tuple(scenario.path(book, batch, 0))
    assert not path[0].snapshot.fixings
    fixing = path[1].snapshot.fixings[0]
    assert path[2].snapshot.fixings == (fixing,)
    assert fixing.source.is_sample
    projected_later = (
        path[2]
        .curves.forward_curve(Currency.USD, coupon.index)
        .simple_rate(dates[2], period.end, coupon.day_count)
    )
    assert fixing.rate != pytest.approx(projected_later, abs=1e-3)
    result = service().run(req, book, scenario, run())
    assert result.positive_paths.shape == (1, 3, 1)
    # A terminated position must not demand future fixings on this grid.
    exited = replace(
        record, effective_date=VALUATION, termination_date=VALUATION, termination_reason="exit"
    )
    exited_book = replace(
        book, counterparties=(replace(cp, netting_sets=(netting(trades=(exited,)),)),)
    )
    assert not tuple(scenario.path(exited_book, batch, 0))[-1].snapshot.fixings


def test_hull_white_conditional_discount_curve_at_cashflow_knots():
    req = request(paths=1, batch=1)
    hw = HullWhite(0.4, 0.01, LinearForwardCurve(0.03, 0.001))
    req = replace(req, components=(replace(req.components[0], process=hw),))
    batch = next(MonteCarloEngine().iter_batches(req))
    path = tuple(markets(req).path(portfolio(), batch, 0))
    for step, market in enumerate(path):
        rate = float(batch.values.array[0, step, 0])
        assert market.curves.discount_curve(Currency.USD).discount(YEAR_ONE) == pytest.approx(
            hw.bond(req.grid.times[step], 1.0, rate), rel=1e-14
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"counterparty_id": "bad"},
        {"baseline": None},
        {"recovery": None},
        {"threshold_key": None},
        {"kind": "bad"},
        {"rho": 2},
        {"rho": 0.1},
        {"rank_key": StreamKey(42, 2)},
        {"kind": DependenceKind.STATIC_RANK},
        {"kind": DependenceKind.STATIC_RANK, "rank_key": StreamKey(42, 1)},
        {"kind": DependenceKind.DYNAMIC_SPREAD},
        {"spread_component": "credit"},
        {"spread_policy": ReducedFormSpread(RecoveryAssumption(0.4))},
        {
            "kind": DependenceKind.DYNAMIC_SPREAD,
            "spread_component": "credit",
            "spread_policy": ReducedFormSpread(RecoveryAssumption(0.2)),
        },
    ],
)
def test_invalid_credit_scenario(changes):
    with pytest.raises(DomainValidationError):
        credit(request(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"request": None},
        {"dates": (VALUATION,)},
        {"dates": (VALUATION, VALUATION)},
        {"dates": (VALUATION, date(2025, 7, 2))},
        {"knot_dates": (YEAR_ONE, YEAR_ONE)},
        {"knot_dates": (date(2025, 2, 1),)},
        {"rates": ()},
        {"rates": (RateBinding(Currency.USD, "usd"),) * 2},
        {"rates": (RateBinding(Currency.USD, "missing"),)},
        {"fx": (FxBinding(Currency.EUR, Currency.USD, "usd"),)},
        {"fx": (FxBinding(Currency.EUR, Currency.USD, "usd"),) * 2},
    ],
)
def test_invalid_conditional_market_configuration(changes):
    with pytest.raises(DomainValidationError):
        markets(request(), **changes)


def test_invalid_binding_units_fixings_and_required_grid_dates():
    with pytest.raises(DomainValidationError):
        RateBinding(Currency.USD, "usd", ("index", "index"))
    with pytest.raises(DomainValidationError):
        FxBinding(Currency.USD, Currency.USD, "fx")
    req = request()
    for change in ({"measure": "P"}, {"state_units": ("bad",)}):
        bad = replace(req, components=(replace(req.components[0], **change),))
        with pytest.raises(DomainValidationError):
            markets(bad)
    from parallax_risk.common.identifiers import QuoteId

    fixing = RateFixing(QuoteId("fix"), Currency.USD, "index", date(2025, 1, 2), 0.03, SOURCE)
    with pytest.raises(DomainValidationError):
        markets(req, initial_fixings=(fixing,))
    fixing = replace(fixing, fixing_date=VALUATION)
    with pytest.raises(DomainValidationError):
        markets(req, initial_fixings=(fixing, fixing))
    batch = next(MonteCarloEngine().iter_batches(req))
    with pytest.raises(DomainValidationError):
        tuple(
            markets(req).path(
                portfolio(), replace(batch, values=FrozenArray.from_array(np.ones((4, 3, 1)))), 0
            )
        )
    # A within-horizon fixing omitted from the grid cannot be silently reconstructed.
    coupon = FloatingRateCashFlow(
        money(),
        AccrualPeriod(date(2025, 2, 1), YEAR_ONE, YEAR_ONE),
        date(2025, 2, 1),
        "USD-SYNTH-1Y",
        DayCount.ACT_365_FIXED,
    )
    cp = portfolio().counterparties[0]
    book = portfolio(
        counterparties=(replace(cp, netting_sets=(netting(trades=(trade(instrument=coupon),)),)),)
    )
    with pytest.raises(DomainValidationError):
        tuple(markets(req).path(book, batch, 0))


def test_service_rejects_inconsistent_inputs_addresses_accounts_and_budget():
    req = request()
    book = portfolio()
    scenario = markets(req)
    candidates = [
        (None, book, scenario, run(), {}),
        (req, None, scenario, run(), {}),
        (req, portfolio(counterparties=()), scenario, run(), {}),
        (req, book, scenario, None, {}),
        (req, book, scenario, replace(run(), seed=99), {}),
        (req, book, markets(replace(req, path_count=4)), run(), {}),
        (req, book, scenario, run(), {"maximum_output_bytes": 1}),
        (req, book, scenario, run(), {"accounts": (account(),)}),
        (
            req,
            book,
            scenario,
            run(),
            {"credit": (credit(req, counterparty_id=CounterpartyId("other")),)},
        ),
        (req, book, scenario, run(), {"credit": (credit(req), credit(req))}),
        (req, book, scenario, run(), {"credit": (credit(req, threshold_key=StreamKey(42)),)}),
        (req, book, scenario, run(), {"credit": (credit(req, threshold_key=StreamKey(99, 1)),)}),
        (
            req,
            book,
            scenario,
            run(),
            {"credit": (credit(req, baseline=PiecewiseHazardCurve((0.0, 1.0), (0.2,))),)},
        ),
        (
            req,
            book,
            scenario,
            run(),
            {"credit": (credit(req, kind=DependenceKind.STATIC_RANK, rank_key=StreamKey(99, 2)),)},
        ),
        (
            req,
            book,
            scenario,
            run(),
            {"credit": (credit(req, kind=DependenceKind.STATIC_RANK, rank_key=StreamKey(42)),)},
        ),
        (
            req,
            book,
            scenario,
            run(),
            {
                "credit": (
                    credit(
                        req,
                        kind=DependenceKind.DYNAMIC_SPREAD,
                        spread_component="usd",
                        spread_policy=ReducedFormSpread(RecoveryAssumption(0.4)),
                    ),
                )
            },
        ),
    ]
    for args in candidates:
        with pytest.raises(DomainValidationError):
            service().run(*args[:4], **args[4])
    collat, ledger = collateral_book()
    with pytest.raises(DomainValidationError):
        service().run(req, collat, scenario, run(), accounts=(ledger,))
    dates = (VALUATION, VALUATION + timedelta(days=1))
    req = request(dates=dates)
    scenario = markets(req, dates)
    cp = collat.counterparties[0]
    scope = cp.netting_sets[0]
    agreement = scope.csa
    from parallax_risk.domain.portfolio.csa import EligibleCollateral

    bad_csa = replace(
        agreement, eligible_collateral=(EligibleCollateral(Currency.USD, Decimal(".1")),)
    )
    bad_book = replace(
        collat, counterparties=(replace(cp, netting_sets=(replace(scope, csa=bad_csa),)),)
    )
    with pytest.raises(DomainValidationError):
        service().run(req, bad_book, scenario, run(), accounts=(ledger,))
    from tests.quantitative.test_collateral_netting import movement

    with pytest.raises(DomainValidationError):
        service().run(req, collat, scenario, run(), accounts=(ledger.append(movement()),))


def test_market_and_simulation_adapter_failures_are_explicit():
    req = request()

    class BadMarkets:
        dates = markets(req).dates
        hash = "a" * 64

        def __init__(self, kind):
            self.kind = kind

        def path(self, book, batch, local):
            path = tuple(markets(req).path(book, batch, local))
            if self.kind == "short":
                yield path[0]
            elif self.kind == "extra":
                yield from (*path, path[-1])
            elif self.kind == "wrong":
                yield path[-1]
            else:
                yield None

    for kind in ("short", "extra", "wrong", "untyped"):
        with pytest.raises(DomainValidationError):
            service().run(req, portfolio(), BadMarkets(kind), run())

    class BadEngine(MonteCarloEngine):
        def __init__(self, kind):
            self.kind = kind

        def iter_batches(self, request):
            batch = next(super().iter_batches(request))
            if self.kind == "short":
                yield batch
            elif self.kind == "wrong":
                yield replace(batch, start_path=1)
            elif self.kind == "long":
                yield replace(batch, values=FrozenArray.from_array(np.ones((10, 2, 1))))
            else:
                yield replace(batch, values=FrozenArray.from_array(np.ones((4, 3, 1))))

    for kind in ("short", "wrong", "long", "shape"):
        with pytest.raises(DomainValidationError):
            service(BadEngine(kind)).run(req, portfolio(), markets(req), run())


def test_initial_and_conflicting_fixings_and_swaps():
    from parallax_risk.common.identifiers import QuoteId
    from parallax_risk.domain.instruments.rates.contracts import InterestRateSwap, SwapDirection
    from tests.fixtures.deterministic import INDEX, PERIODS, SOURCE

    req = request(paths=1, batch=1)
    swap = InterestRateSwap(
        money(100),
        0.03,
        PERIODS,
        PERIODS,
        (VALUATION, YEAR_ONE),
        INDEX,
        DayCount.ACT_365_FIXED,
        DayCount.ACT_365_FIXED,
        SwapDirection.PAY_FIXED,
    )
    cp = portfolio().counterparties[0]
    record = trade(instrument=swap)
    book = portfolio(counterparties=(replace(cp, netting_sets=(netting(trades=(record,)),)),))
    fixing = RateFixing(QuoteId("initial-fixing"), Currency.USD, INDEX, VALUATION, 0.031, SOURCE)
    scenario = markets(req, initial_fixings=(fixing,))
    result = service().run(req, book, scenario, run())
    assert result.positive_paths.shape == (1, 2, 1)
    # Conflicting index tenor uses the same fixing key and is rejected.
    other = FloatingRateCashFlow(
        money(),
        AccrualPeriod(VALUATION, date(2025, 10, 1), date(2025, 10, 1)),
        VALUATION,
        INDEX,
        DayCount.ACT_365_FIXED,
    )
    book = portfolio(
        counterparties=(
            replace(cp, netting_sets=(netting(trades=(record, trade("other", instrument=other))),)),
        )
    )
    with pytest.raises(DomainValidationError):
        service().run(req, book, scenario, run())


def test_multiple_counterparty_credit_addresses_and_market_origin_rejections():
    req = request(paths=1, batch=1)
    cp = portfolio().counterparties[0]
    other = replace(
        cp,
        counterparty_id=CounterpartyId("other"),
        netting_sets=(netting(netting_set_id=NettingSetId("other"), trades=(trade("other"),)),),
    )
    book = portfolio(counterparties=(cp, other))
    same = (credit(req), credit(req, book=replace(book, counterparties=(other,))))
    with pytest.raises(DomainValidationError):
        service().run(req, book, markets(req), run(), credit=same)
    first = replace(same[0], kind=DependenceKind.STATIC_RANK, rank_key=StreamKey(42, 3))
    second = replace(
        same[1],
        threshold_key=StreamKey(42, 2),
        kind=DependenceKind.STATIC_RANK,
        rank_key=StreamKey(42, 3),
    )
    with pytest.raises(DomainValidationError):
        service().run(req, book, markets(req), run(), credit=(first, second))
    second = replace(second, rank_key=StreamKey(42, 4))
    result = service().run(req, book, markets(req), run(), credit=(first, second))
    assert len(result.counterparties) == 2
    assert result.counterparties[0].baseline_survival[0] == 1

    class WrongOrigin:
        dates = (date(2024, 1, 1), date(2025, 7, 1))
        hash = "a" * 64

    with pytest.raises(DomainValidationError):
        service().run(req, portfolio(), WrongOrigin(), run())


def test_spread_protocol_accepts_custom_policy_and_rejects_bad_hash():
    class CustomPolicy:
        recovery = RecoveryAssumption(0.4)
        hash = "b" * 64

        def intensity(self, spread):
            return spread / 0.6

    req = fx_request(paths=2, batch=2)
    scenario = credit(
        req,
        kind=DependenceKind.DYNAMIC_SPREAD,
        spread_component="credit",
        spread_policy=CustomPolicy(),
    )
    assert len(scenario.hash) == 64
    assert service().run(req, fx_book(), fx_markets(req), run(), credit=(scenario,)).counterparties
    CustomPolicy.hash = "bad"
    with pytest.raises(DomainValidationError):
        credit(
            req,
            kind=DependenceKind.DYNAMIC_SPREAD,
            spread_component="credit",
            spread_policy=CustomPolicy(),
        )
