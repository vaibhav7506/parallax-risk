"""Actual exposure/XVA revaluation, common streams, policy rejection and attribution."""

import math
from dataclasses import replace
from datetime import date

import pytest

from parallax_risk.application.xva import XvaService
from parallax_risk.application.xva_revaluation import FactorMove
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.identifiers import CounterpartyId, NettingSetId, TradeId
from parallax_risk.domain.credit.dependence import ReducedFormSpread
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.xva.contracts import ComponentKind
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor
from tests.fixtures.deterministic import money
from tests.fixtures.exposure import collateral_book, markets, request
from tests.fixtures.portfolio import run
from tests.fixtures.xva import curve, experiment, funding, margin, own, revaluation


def test_synthetic_production_example():
    from parallax_risk.application.xva_examples import example

    first = example(4)
    assert first == example(4)
    assert len(first.valuations) == 3
    assert first.attribution.unexplained_change == 0
    assert str(first.inputs.run.run_id) == "synthetic-phase7"


def test_two_entities_are_summed_without_netting_or_shared_credit_bump():
    from decimal import Decimal

    e = experiment(paths=4, kind=2)
    cp = e.book.counterparties[0]
    scope = cp.netting_sets[0]
    second = replace(
        cp,
        counterparty_id=CounterpartyId("z-other"),
        netting_sets=(
            replace(
                scope,
                netting_set_id=NettingSetId("z-other-set"),
                trades=(
                    replace(
                        scope.trades[0], trade_id=TradeId("z-other-trade"), quantity=Decimal(-1)
                    ),
                ),
            ),
        ),
    )
    book = replace(e.book, counterparties=(cp, second))
    e = replace(
        e,
        book=book,
        credit=(
            e.credit[0],
            replace(
                e.credit[0],
                counterparty_id=second.counterparty_id,
                threshold_key=StreamKey(e.run.seed, 3),
            ),
        ),
        margins=(e.margins[0], e.margins[0]),
    )
    workflow = revaluation()
    r = workflow.value(e)
    assert len(r.counterparties) == 2
    for kind in ComponentKind:
        assert float(r.result.component(kind).adjustment.amount) == pytest.approx(
            math.fsum(float(c.result.component(kind).adjustment.amount) for c in r.counterparties),
            rel=0.0,
            abs=1e-12,
        )
        assert r.result.component(kind).contribution_labels == ("synthetic-cp", "z-other")
    assert r.result.component(ComponentKind.CVA).adjustment.amount < 0
    assert r.result.component(ComponentKind.DVA).adjustment.amount > 0
    with pytest.raises(ParallaxError, match="shared spread"):
        workflow.bump(e, RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"), 0.001)


def test_custom_spread_policy_is_used_but_cannot_be_silently_replaced():
    class CustomPolicy:
        hash = "f" * 64
        recovery = RecoveryAssumption(0.4)

        def intensity(self, spread):
            return spread / 0.6

    e = experiment(paths=4, kind=2)
    e = replace(e, credit=(replace(e.credit[0], spread_policy=CustomPolicy()),))
    workflow = revaluation()
    assert workflow.value(e).result.hash
    for kind in (FactorKind.CREDIT_SPREAD, FactorKind.RECOVERY):
        with pytest.raises(ParallaxError, match="credit-triangle"):
            workflow.bump(e, RiskFactor(kind, "synthetic-cp"), 0.001)


def test_correlation_bump_preserves_policy_or_constructs_explicit_identity():
    e = experiment(paths=4)
    workflow = revaluation()
    f = RiskFactor(FactorKind.CORRELATION, "fx.d0", "spread.d0")
    for correlation in (None, replace(e.request.correlation, psd_tolerance=1e-10)):
        req = replace(e.request, correlation=correlation)
        state = replace(e, request=req, markets=replace(e.markets, request=req))
        moved = workflow.bump(state, f, 0.001)
        assert moved.request.correlation.psd_tolerance == (1e-12 if correlation is None else 1e-10)
        assert workflow.value(moved).result.hash


def test_experiment_and_revaluation_invalid_boundaries():
    e = experiment(paths=4)
    workflow = revaluation()
    for changes in (
        {"run": None},
        {"own": None},
        {"markets": replace(e.markets, request=replace(e.request, path_count=8))},
    ):
        with pytest.raises(ParallaxError):
            replace(e, **changes)
    for args in ((None, RiskFactor(FactorKind.FX, "fx"), 0.01), (e, None, 0.01)):
        with pytest.raises(ParallaxError):
            workflow.bump(*args)
    with pytest.raises(ParallaxError):
        workflow.value(None)
    with pytest.raises(ParallaxError):
        workflow.sensitivity(e, None, 0.01)
    full = replace(e, credit=(replace(e.credit[0], recovery=RecoveryAssumption(1)),))
    with pytest.raises(ParallaxError):
        workflow.bump(full, RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"), 0.001)
    assert workflow.bump(e, RiskFactor(FactorKind.FX, "fx"), 0.0) == e


def test_unsupported_heston_vega_has_no_fallback():
    from parallax_risk.domain.models.assets import Heston
    from parallax_risk.domain.simulation.contracts import ProcessComponent, Scheme

    e = experiment(paths=4)
    item = ProcessComponent(
        "unused",
        Heston(1.0, 0.04, 0.2, -0.5, 0.03),
        (100.0, 0.04),
        Scheme.HESTON_PROJECTED,
        ("USD", "annual_variance"),
        "Q",
    )
    req = replace(e.request, components=(*e.request.components, item), correlation=None)
    e = replace(e, request=req, markets=replace(e.markets, request=req))
    with pytest.raises(ParallaxError, match="Vega supports"):
        revaluation().bump(e, RiskFactor(FactorKind.VOLATILITY, "unused"), 0.001)


def collateral_experiment():
    e = experiment(paths=4)
    dates = (date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4))
    req = request(paths=4, batch=4, dates=dates)
    book, account = collateral_book(lag=0)
    cp = book.counterparties[0]
    scope = cp.netting_sets[0]
    scope = replace(
        scope,
        csa=replace(
            scope.csa,
            receive_threshold=scope.csa.receive_threshold + money(5, scope.csa.currency),
        ),
    )
    # Use exact existing Money helper to keep all CSA fields validated.
    book = replace(book, counterparties=(replace(cp, netting_sets=(scope,)),))
    credit = CreditScenario(
        cp.counterparty_id,
        PiecewiseHazardCurve((0.0, req.grid.times[-1]), (0.2,)),
        RecoveryAssumption(0.4),
        StreamKey(42, 1),
    )
    return replace(
        e,
        request=req,
        book=book,
        markets=markets(req, dates),
        accounts=(account,),
        credit=(credit,),
        own=own(req.grid.times[-1]),
        discount=curve(req.grid.times),
        funding=funding(req.grid.times[-1]),
        margins=(margin(req.grid.times),),
        run=run(),
    )


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_actual_xva_service_independent_static_and_dynamic(kind):
    e = experiment(kind=kind)
    workflow = revaluation()
    first = workflow.value(e)
    assert first == workflow.value(e)
    assert first.context == e.run and len(first.exposure_hash) == 64
    assert first.result.component(ComponentKind.CVA).adjustment.amount <= 0
    assert first.result.component(ComponentKind.DVA).adjustment.amount >= 0
    assert float(first.result.total_adjustment.amount) == pytest.approx(
        math.fsum(float(c.adjustment.amount) for c in first.result.components), rel=0.0, abs=1e-12
    )
    method = first.counterparties[0].result.component(ComponentKind.CVA).methodology
    assert ("independent_" if kind == 0 else "sampled_default") in method


@pytest.mark.parametrize(
    "factor,bump",
    [
        (RiskFactor(FactorKind.RATE, "usd"), 1e-4),
        (RiskFactor(FactorKind.FX, "fx"), 1e-3),
        (RiskFactor(FactorKind.VOLATILITY, "fx"), 1e-3),
        (RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"), 1e-4),
        (RiskFactor(FactorKind.RECOVERY, "synthetic-cp"), 1e-3),
        (RiskFactor(FactorKind.CORRELATION, "fx.d0", "spread.d0"), 1e-3),
    ],
)
def test_all_market_credit_sensitivities_reprice_actual_paths(factor, bump):
    e = experiment(paths=32)
    workflow = revaluation()
    risk = workflow.sensitivity(e, factor, bump)
    assert len(risk.components) == 5 and risk.factor == factor
    assert risk.base.input_hash != risk.up.input_hash != risk.down.input_hash
    assert all(math.isfinite(c.derivative_per_unit) for c in risk.components)
    assert risk.components[-1].derivative_per_unit == pytest.approx(
        math.fsum(c.derivative_per_unit for c in risk.components[:-1]), rel=0.0, abs=1e-9
    )
    moved = workflow.bump(e, factor, bump)
    assert moved.request.sequence == e.request.sequence
    assert moved.run == e.run
    assert tuple(c.threshold_key for c in moved.credit) == tuple(c.threshold_key for c in e.credit)
    cva = risk.components[0].derivative_per_unit
    if factor.kind in (FactorKind.FX, FactorKind.CREDIT_SPREAD):
        assert cva < 0
    if factor.kind == FactorKind.RECOVERY:
        assert cva > 0
    if factor.kind in (FactorKind.FX, FactorKind.CREDIT_SPREAD, FactorKind.RECOVERY):
        assert risk.components[0].absolute_stability_difference < 1e-4 * max(1, abs(cva))


def test_collateral_threshold_sensitivity_and_full_recovery():
    e = collateral_experiment()
    workflow = revaluation()
    factor = RiskFactor(
        FactorKind.COLLATERAL, str(e.book.counterparties[0].netting_sets[0].netting_set_id)
    )
    risk = workflow.sensitivity(e, factor, 0.5)
    assert risk.components[0].derivative_per_unit < 0
    assert risk.components[0].absolute_stability_difference < 1e-10
    c = replace(e.credit[0], recovery=RecoveryAssumption(1))
    r = workflow.value(replace(e, credit=(c,)))
    assert r.result.component(ComponentKind.CVA).adjustment.amount == 0


def test_rate_bump_preserves_declared_fx_drift_relation_and_hull_white_shift():
    e = experiment()
    workflow = revaluation()
    shifted = workflow.bump(e, RiskFactor(FactorKind.RATE, "usd"), 0.01)
    assert shifted.request.components[2].process.drift_rate == pytest.approx(
        0.01, rel=0.0, abs=1e-15
    )
    assert shifted.discount.discount(shifted.request.grid.times[-1]) < e.discount.discount(
        e.request.grid.times[-1]
    )
    shifted = workflow.bump(e, RiskFactor(FactorKind.RATE, "eur"), 0.01)
    assert shifted.request.components[2].process.drift_rate == pytest.approx(
        -0.01, rel=0.0, abs=1e-15
    )
    assert shifted.discount == e.discount
    req = replace(
        e.request,
        components=(
            replace(
                e.request.components[0], process=HullWhite(0.4, 0.01, LinearForwardCurve(0.03))
            ),
            *e.request.components[1:],
        ),
    )
    hw = replace(e, request=req, markets=replace(e.markets, request=req))
    moved = workflow.bump(hw, RiskFactor(FactorKind.RATE, "usd"), 0.001)
    assert moved.request.components[0].process.initial_curve.level == pytest.approx(
        0.031, rel=0.0, abs=1e-15
    )
    assert workflow.value(moved).result.hash


def test_dynamic_credit_spread_and_recovery_bumps_update_intensity_policy():
    e = experiment(kind=2)
    workflow = revaluation()
    for factor, amount in [
        (RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"), 0.001),
        (RiskFactor(FactorKind.RECOVERY, "synthetic-cp"), 0.01),
    ]:
        moved = workflow.bump(e, factor, amount)
        assert isinstance(moved.credit[0].spread_policy, ReducedFormSpread)
        assert moved.credit[0].spread_policy.recovery == moved.credit[0].recovery
        assert workflow.value(moved).result.hash != workflow.value(e).result.hash


def test_sequential_attribution_reconciles_components_and_exposes_omitted_factor():
    e = experiment(paths=8)
    workflow = revaluation()
    fx = RiskFactor(FactorKind.FX, "fx")
    credit = RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp")
    moves = (FactorMove("spot", fx, 0.02), FactorMove("credit", credit, 0.002))
    actual = workflow.bump(workflow.bump(e, fx, 0.02), credit, 0.002)
    complete = workflow.attribute(e, moves, actual)
    assert complete.unexplained_change == 0
    assert complete.total_change == pytest.approx(complete.explained_change, rel=0.0, abs=1e-12)
    assert all(v == 0 for v in complete.component_residuals)
    partial = workflow.attribute(e, moves[:1], actual)
    assert abs(partial.unexplained_change) > 1e-4
    assert partial.total_change == pytest.approx(
        partial.explained_change + partial.unexplained_change, rel=0.0, abs=1e-12
    )


@pytest.mark.parametrize(
    "factor,amount",
    [
        (RiskFactor(FactorKind.FX, "fx"), -2),
        (RiskFactor(FactorKind.FX, "usd"), 0.01),
        (RiskFactor(FactorKind.RATE, "fx"), 0.01),
        (RiskFactor(FactorKind.VOLATILITY, "fx"), -1),
        (RiskFactor(FactorKind.CREDIT_SPREAD, "missing"), 0.01),
        (RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"), -1),
        (RiskFactor(FactorKind.RECOVERY, "synthetic-cp"), 1),
        (RiskFactor(FactorKind.CORRELATION, "fx.d0", "spread.d0"), 1),
        (RiskFactor(FactorKind.CORRELATION, "bad", "spread.d0"), 0.1),
        (RiskFactor(FactorKind.COLLATERAL, "synthetic-set"), 1),
        (RiskFactor(FactorKind.FX, "fx"), 1e-100),
    ],
)
def test_invalid_bumps_reject_without_repair(factor, amount):
    with pytest.raises(ParallaxError):
        revaluation().bump(experiment(), factor, amount)


def test_xva_service_rejects_foreign_stale_and_missing_evidence():
    e = experiment(paths=4)
    w = revaluation()
    paths = w.exposure.run(e.request, e.book, e.markets, e.run, credit=e.credit)
    calls = [
        (paths, e.discount, (), e.own, e.funding, e.margins, e.run),
        (paths, e.discount, e.credit, e.own, e.funding, (), e.run),
        (
            paths,
            replace(e.discount, valuation_date=date(2024, 1, 1)),
            e.credit,
            e.own,
            e.funding,
            e.margins,
            e.run,
        ),
        (None, e.discount, e.credit, e.own, e.funding, e.margins, e.run),
        (paths, e.discount, e.credit, e.own, e.funding, e.margins, None),
        (
            paths,
            e.discount,
            (replace(e.credit[0], recovery=RecoveryAssumption(0.5)),),
            e.own,
            e.funding,
            e.margins,
            e.run,
        ),
    ]
    for args in calls:
        with pytest.raises(ParallaxError):
            w.xva.value(*args)

    class BadCalculator:
        def calculate(self, *args, **kwargs):
            return None

    bad = XvaService(BadCalculator(), w.xva.logger)
    with pytest.raises(ParallaxError):
        bad.value(paths, e.discount, e.credit, e.own, e.funding, e.margins, e.run)

    class StaleCalculator:
        def calculate(self, *args, **kwargs):
            from tests.fixtures.xva import result

            return result()

    stale = XvaService(StaleCalculator(), w.xva.logger)
    with pytest.raises(ParallaxError, match="stale/foreign"):
        stale.value(paths, e.discount, e.credit, e.own, e.funding, e.margins, e.run)
