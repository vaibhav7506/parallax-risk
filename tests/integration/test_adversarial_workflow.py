"""Actual production exposure/XVA challenger, six-factor mapping and machine evidence."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from parallax_risk.application.adversarial_examples import example
from parallax_risk.application.validation_forensics import xva_context
from parallax_risk.application.validation_models import ProductionXvaModel
from parallax_risk.application.validation_search import search
from parallax_risk.application.validation_search_models import (
    IndependentCreditCvaChallenger,
    XvaCvaProduction,
    XvaSearchCases,
)
from parallax_risk.application.validation_stress import factor_unit
from parallax_risk.common.canonical import canonical_value, content_hash
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.search import SearchDimension, SearchSpec
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution
from tests.fixtures.portfolio import account, csa
from tests.fixtures.xva import experiment, revaluation


def daily_case():
    case = experiment(4)
    dates = tuple(case.book.as_of + timedelta(days=i) for i in range(11))
    times = tuple(year_fraction(case.book.as_of, d, DayCount.ACT_365_FIXED) for d in dates)
    request = replace(case.request, grid=TimeGrid(times))
    cp = case.book.counterparties[0]
    n = cp.netting_sets[0]
    agreement = csa(first_margin_date=case.book.as_of, settlement_lag_days=0)
    book = replace(
        case.book, counterparties=(replace(cp, netting_sets=(replace(n, csa=agreement),)),)
    )
    accounts = (
        account(
            netting_set_id=n.netting_set_id, csa_id=agreement.csa_id, opening_date=case.book.as_of
        ),
    )
    margins = tuple(
        replace(m, times=times, posted_initial_margin=(10.0,) * len(times)) for m in case.margins
    )
    return replace(
        case,
        request=request,
        markets=replace(case.markets, request=request, dates=dates),
        book=book,
        accounts=accounts,
        margins=margins,
        credit=tuple(
            replace(c, baseline=replace(c.baseline, times=(0.0, times[-1]))) for c in case.credit
        ),
    )


def test_real_production_and_independent_credit_quadrature_are_comparable():
    case = experiment(4)
    workflow = revaluation()
    p = XvaCvaProduction(ProductionXvaModel(workflow)).evaluate(case)
    c = IndependentCreditCvaChallenger(workflow).evaluate(case)
    assert p.case_hash == c.case_hash == case.hash
    assert p.metric("CVA").schema == c.metric("CVA").schema
    assert p.metric("CVA").value < 0 and c.metric("CVA").value < 0
    # Independent integrals differ from endpoint averaging on this nonflat EE grid.
    assert abs(p.metric("CVA").value - c.metric("CVA").value) > 1e-6


def test_six_factor_search_maps_and_revalues_actual_daily_csa_experiment():
    baseline = daily_case()
    workflow = revaluation()
    factors = (
        RiskFactor(FactorKind.RATE, "usd"),
        RiskFactor(FactorKind.VOLATILITY, "fx"),
        RiskFactor(
            FactorKind.CORRELATION,
            baseline.request.factor_names[2],
            baseline.request.factor_names[3],
        ),
        RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp"),
        RiskFactor(FactorKind.RECOVERY, "synthetic-cp"),
        RiskFactor(
            FactorKind.COLLATERAL,
            str(baseline.book.counterparties[0].netting_sets[0].netting_set_id),
        ),
    )
    ranges = (
        (-0.001, 0.001),
        (-0.05, 0.05),
        (-0.05, 0.05),
        (-0.001, 0.001),
        (-0.05, 0.05),
        (-1.0, 1.0),
    )
    dimensions = tuple(
        SearchDimension(f"factor-{i}", factor_unit(f), lo, hi, "Synthetic admissible delta range")
        for i, (f, (lo, hi)) in enumerate(zip(factors, ranges, strict=True))
    )
    builder = XvaSearchCases(workflow, baseline, factors, dimensions)
    moved = builder((0.001, 0.05, -0.05, 0.001, -0.05, 1.0))
    assert moved.hash != baseline.hash
    assert moved.book.counterparties[0].netting_sets[0].csa.receive_threshold.amount == 11
    spec = SearchSpec(
        dimensions, (), StreamKey(20261001, 1001, 0), "CVA", "Synthetic six-factor bounds", 0, 1, 6
    )
    result = search(
        XvaCvaProduction(ProductionXvaModel(workflow)),
        IndependentCreditCvaChallenger(workflow),
        builder,
        ScipyDifferentialEvolution(),
        spec,
    )
    assert result.optimizer.evaluations == 6
    assert not result.optimizer.converged
    assert all(e.production.case_hash == e.challenger.case_hash for e in result.evaluations)
    old_context = xva_context(baseline, content_hash("No calibration supplied"))
    new_context = xva_context(moved, content_hash("No calibration supplied"))
    assert old_context.market != new_context.market
    assert old_context.parameters != new_context.parameters
    assert old_context.collateral != new_context.collateral
    assert old_context.calibration == new_context.calibration
    assert old_context.numerics == new_context.numerics


def test_xva_challenger_rejects_wwr_and_invalid_context_inputs():
    workflow = revaluation()
    for case in (None, experiment(4, 1), experiment(4, 2)):
        with pytest.raises(ParallaxError):
            IndependentCreditCvaChallenger(workflow).evaluate(case)
    with pytest.raises(ParallaxError):
        xva_context(None, content_hash("no calibration"))
    with pytest.raises(ParallaxError):
        xva_context(experiment(4), "fake")


def test_xva_builder_rejects_units_duplicates_bounds_and_unsupported_domains():
    case = experiment(4)
    workflow = revaluation()
    f = RiskFactor(FactorKind.VOLATILITY, "fx")
    d = SearchDimension("vega", factor_unit(f), -0.1, 0.1, "Synthetic interval")
    with pytest.raises(ParallaxError):
        XvaSearchCases(workflow, case, (f,), (replace(d, unit="percent"),))
    with pytest.raises(ParallaxError):
        XvaSearchCases(workflow, case, (f, f), (d, d))
    builder = XvaSearchCases(workflow, case, (f,), (d,))
    with pytest.raises(ParallaxError):
        builder((0.2,))
    with pytest.raises(ParallaxError):
        builder((0.0, 0.0))
    # A caller-declared range is not permission to make economic inputs invalid.
    invalid = XvaSearchCases(workflow, case, (f,), (replace(d, lower=-1.0),))
    with pytest.raises(ParallaxError):
        invalid((-0.9,))


def test_machine_evidence_replays_without_unsupported_arrays_or_nonfinite_json():
    first = json.dumps(
        canonical_value(example(ScipyDifferentialEvolution())), sort_keys=True, allow_nan=False
    )
    second = json.dumps(
        canonical_value(example(ScipyDifferentialEvolution())), sort_keys=True, allow_nan=False
    )
    assert first == second
    assert '"detected": false' in first
    assert '"converged": false' in first
    assert '"residual":' in first


def test_challenger_rejects_failed_quadrature_and_foreign_counterparty(monkeypatch):
    workflow = revaluation()
    case = experiment(4)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            "parallax_risk.application.validation_search_models.quad",
            lambda *args, **kwargs: (0.0, 1.0),
        )
        with pytest.raises(ParallaxError, match="error criterion"):
            IndependentCreditCvaChallenger(workflow).evaluate(case)
    paths = workflow.exposure.run(
        case.request, case.book, case.markets, case.run, credit=case.credit
    )
    from parallax_risk.common.identifiers import CounterpartyId

    class ForeignExposure:
        def run(self, *args, **kwargs):
            return replace(
                paths,
                counterparties=(
                    replace(paths.counterparties[0], counterparty_id=CounterpartyId("foreign")),
                ),
            )

    with pytest.raises(ParallaxError, match="order"):
        IndependentCreditCvaChallenger(replace(workflow, exposure=ForeignExposure())).evaluate(case)
