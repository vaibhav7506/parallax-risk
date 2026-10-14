"""Invalid validation inputs fail explicitly; adapters cannot substitute stale evidence."""

from dataclasses import replace

import numpy as np
import pytest

from parallax_risk.application.validation import ValidationLab, perturbation_band
from parallax_risk.application.validation_invariants import cva_invariants
from parallax_risk.application.validation_models import ProductionCvaModel
from parallax_risk.application.validation_stress import (
    HistoricalObservation,
    ScenarioKind,
    StressScenario,
    combine,
    historical_scenario,
)
from parallax_risk.application.xva_revaluation import FactorMove
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import ParallaxError
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.simulation.statistics import OnlineMoments
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase, IndependentCvaBenchmark
from parallax_risk.domain.validation.checks import (
    ConvergenceAxis,
    ConvergencePoint,
    convergence,
    monotonicity,
    sensitivity,
)
from parallax_risk.domain.validation.contracts import (
    Contribution,
    Finding,
    FindingStatus,
    Metric,
    Severity,
    Tolerance,
    check,
    compare,
)
from parallax_risk.domain.validation.uncertainty import (
    IidUnitResampler,
    IndependentObservations,
    UncertaintyBand,
    bootstrap,
    propagate_covariance,
)
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor

CASE = CvaBenchmarkCase((0.0, 1.0), (100.0, 100.0), Currency.USD, 0.0, 0.2, 0.4)
MODEL = ProductionCvaModel()
OUTPUT = MODEL.evaluate(CASE)
METRIC = Metric("risk", 1.0, "USD")
DATA = IndependentObservations("risk", "USD", (1.0, 2.0), "iid_path", 2, CASE.hash)
MOVE = FactorMove("fx", RiskFactor(FactorKind.FX, "fx"), 0.01)
SCENARIO = StressScenario(
    "synthetic", ScenarioKind.HYPOTHETICAL, (MOVE,), "Synthetic input", "Hypothetical shock"
)
moments = OnlineMoments()
moments.update(np.array([0.9, 1.1]))
ESTIMATE = moments.estimate(total_paths=2, sampling_unit="iid_path")
POINT = ConvergencePoint(2.0, ESTIMATE, CASE.hash)


@pytest.mark.parametrize(
    "changes",
    [
        {"times": (0.1, 1.0)},
        {"times": (0.0, 0.0)},
        {"exposure": (1.0,)},
        {"exposure": (1.0, -1.0)},
        {"hazard": -0.1},
        {"recovery": 1.1},
        {"rate": float("nan")},
        {"rate": -1000.0},
        {"rate": 1000.0},
        {"currency": "USD"},
    ],
)
def test_benchmark_guards(changes):
    with pytest.raises(ParallaxError):
        replace(CASE, **changes)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Contribution("", 1.0),
        lambda: Contribution("x", float("inf")),
        lambda: Metric("x", 1.0, ""),
        lambda: Metric("x", True, "USD"),
        lambda: Metric("x", 1.0, "USD", (Contribution("a", 1.0), Contribution("a", 2.0))),
        lambda: Tolerance(-1),
        lambda: Tolerance(0, -1),
        lambda: Tolerance(0, float("nan")),
        lambda: replace(OUTPUT, metrics=()),
        lambda: replace(OUTPUT, metrics=OUTPUT.metrics * 2),
        lambda: replace(OUTPUT, assumptions=("",)),
        lambda: replace(OUTPUT, evidence_hash="bad"),
        lambda: Finding("finding", "high", ("evidence",), "risk", "run", "v"),
        lambda: Finding("finding", Severity.HIGH, ("",), "risk", "run", "v"),
        lambda: Finding("finding", Severity.HIGH, ("evidence",), "risk", "run", "v", "open"),
        lambda: check("bad", METRIC, -1, 0, evidence=("e",), reproduction="run", version="v"),
        lambda: check("bad", METRIC, 0, -1, evidence=("e",), reproduction="run", version="v"),
        lambda: check("bad", "risk", 0, 0, evidence=("e",), reproduction="run", version="v"),
        lambda: OUTPUT.metric("absent"),
        lambda: MODEL.evaluate("bad"),
        lambda: IndependentCvaBenchmark().evaluate("bad"),
    ],
)
def test_metric_and_finding_guards(factory):
    with pytest.raises(ParallaxError):
        factory()


@pytest.mark.parametrize(
    "other",
    [
        replace(OUTPUT, case_hash="a" * 64),
        replace(OUTPUT, metrics=(Metric("CVA", 1.0, "EUR", (Contribution("credit", 1.0),)),)),
        replace(OUTPUT, metrics=(Metric("CVA", 1.0, "USD"),)),
        replace(OUTPUT, metrics=(Metric("CVA", 1.0, "USD", (Contribution("other", 1.0),)),)),
    ],
)
def test_comparison_rejects_incompatible_inputs_units_or_components(other):
    with pytest.raises(ParallaxError):
        compare(OUTPUT, other, Tolerance(0), "run case")


def test_decomposition_retains_unexplained_difference_and_resolution_status():
    p = replace(OUTPUT, metrics=(Metric("risk", 10.0, "USD", (Contribution("a", 8.0),)),))
    c = replace(
        p,
        model_name="challenger",
        metrics=(Metric("risk", 14.0, "USD", (Contribution("a", 9.0),)),),
    )
    difference = compare(p, c, Tolerance(0), "Run retained mathematical target").differences[0]
    assert (
        difference.difference == 4
        and difference.contributions[0].value == 1
        and difference.residual == 3
    )
    finding = difference.check.finding
    assert replace(finding, status=FindingStatus.RESOLVED).status == "resolved"
    assert finding.status == "open"  # Immutable evidence; no governance approval inferred.


def test_stale_models_and_ensemble_budget_are_rejected():
    class Stale:
        def evaluate(self, case):
            return OUTPUT

    with pytest.raises(ParallaxError):
        ValidationLab(Stale(), Stale()).compare(replace(CASE, hazard=0.1), Tolerance(0), "run")
    for kwargs in ({"cases": ()}, {"maximum_evaluations": 1}, {"confidence": 1.0}):
        arguments = {
            "model": MODEL,
            "baseline": CASE,
            "cases": (CASE, replace(CASE, hazard=0.1)),
            "metric": "CVA",
        } | kwargs
        with pytest.raises(ParallaxError):
            perturbation_band(**arguments)
    with pytest.raises(ParallaxError):
        perturbation_band(Stale(), CASE, (CASE, replace(CASE, hazard=0.1)), "CVA")


@pytest.mark.parametrize(
    "changes",
    [
        {"values": (1.0,)},
        {"values": (1.0, float("inf"))},
        {"sampling_unit": "sobol_points"},
        {"total_paths": 3},
        {"sampling_unit": "antithetic_pair"},
    ],
)
def test_independent_unit_guards(changes):
    with pytest.raises(ParallaxError):
        replace(DATA, **changes)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"confidence": 0.0},
        {"confidence": 1.0},
        {"replicates": 1},
        {"maximum_draws": 3},
        {"key": 1},
        {"data": "bad"},
    ],
)
def test_bootstrap_guards_and_budget(kwargs):
    arguments = {
        "data": DATA,
        "key": StreamKey(1),
        "resampler": IidUnitResampler(),
        "statistic": sum,
        "statistic_name": "sum",
        "replicates": 10,
    } | kwargs
    with pytest.raises(ParallaxError):
        bootstrap(**arguments)


def test_resampler_port_cannot_change_units_or_return_nonfinite_values():
    class Bad:
        method = "invalid-sized-example"

        def resample(self, values, key, replicate):
            return values[:1]

    with pytest.raises(ParallaxError, match="sample size"):
        bootstrap(DATA, StreamKey(1), Bad(), sum, statistic_name="sum", replicates=2)
    with pytest.raises(ParallaxError):
        IidUnitResampler().resample(DATA.values, 1, 0)
    with pytest.raises(ParallaxError):
        IidUnitResampler().resample((float("inf"),), StreamKey(1), 0)


@pytest.mark.parametrize(
    "covariance",
    [
        ((1.0, 2.0),),
        ((1.0, 1.0), (0.0, 1.0)),
        ((1.0, 2.0), (2.0, 1.0)),
        ((float("inf"), 0.0), (0.0, 1.0)),
        ((1.0,), (0.0, 1.0)),
    ],
)
def test_covariance_rejects_invalid_shape_asymmetry_and_indefiniteness(covariance):
    with pytest.raises(ParallaxError):
        propagate_covariance(METRIC, (1.0, 1.0), covariance, ("rate", "rate"), CASE.hash)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: propagate_covariance("bad", (1.0,), ((1.0,),), ("rate",), CASE.hash),
        lambda: propagate_covariance(METRIC, (1.0,), ((1.0,),), (), CASE.hash),
        lambda: propagate_covariance(METRIC, (1e308,), ((1e308,),), ("rate",), CASE.hash),
        lambda: replace(
            UncertaintyBand(
                "risk", "USD", 1.0, 0.0, 2.0, 0.95, "method", CASE.hash, ("assumption",)
            ),
            lower=3.0,
        ),
        lambda: monotonicity(
            "x",
            (METRIC,),
            increasing=True,
            tolerance=Tolerance(0),
            evidence=("e",),
            reproduction="run",
            version="v",
        ),
        lambda: monotonicity(
            "x",
            (METRIC, replace(METRIC, unit="EUR")),
            increasing=True,
            tolerance=Tolerance(0),
            evidence=("e",),
            reproduction="run",
            version="v",
        ),
        lambda: sensitivity(
            lambda x: METRIC,
            0.0,
            "rate",
            Tolerance(0),
            evidence=("e",),
            reproduction="run",
            version="v",
        ),
        lambda: cva_invariants(MODEL, CASE, Tolerance(0), "run", scale=0),
        lambda: cva_invariants(MODEL, CASE, Tolerance(0), "run", collateral=-1),
    ],
)
def test_numerical_guards(factory):
    with pytest.raises(ParallaxError):
        factory()


@pytest.mark.parametrize(
    "changes",
    [
        {"resolution": 0},
        {"estimate": "bad"},
        {"estimate": replace(ESTIMATE, independent_units=1)},
        {"estimate": replace(ESTIMATE, confidence_interval=(2.0, 3.0))},
        {"estimate": replace(ESTIMATE, sample_variance=-1.0)},
    ],
)
def test_convergence_point_guards(changes):
    with pytest.raises(ParallaxError):
        replace(POINT, **changes)


@pytest.mark.parametrize(
    "axis,points",
    [
        ("path_count", (POINT, POINT)),
        (ConvergenceAxis.PATH_COUNT, (POINT,)),
        (ConvergenceAxis.PATH_COUNT, (POINT, POINT)),
        (ConvergenceAxis.TIME_STEP, (POINT, replace(POINT, resolution=3.0))),
        (ConvergenceAxis.PATH_COUNT, (POINT, replace(POINT, resolution=3.0))),
        (
            ConvergenceAxis.TIME_STEP,
            (
                POINT,
                replace(
                    POINT,
                    resolution=1.0,
                    estimate=moments.estimate(
                        total_paths=2, sampling_unit="iid_path", confidence=0.9
                    ),
                ),
            ),
        ),
    ],
)
def test_convergence_ladder_guards(axis, points):
    with pytest.raises(ParallaxError):
        convergence(
            axis, "risk", "USD", points, Tolerance(0), Tolerance(0), reproduction="run", version="v"
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: replace(SCENARIO, moves=(MOVE, MOVE)),
        lambda: replace(SCENARIO, kind="hypothetical"),
        lambda: replace(SCENARIO, kind=ScenarioKind.HISTORICAL),
        lambda: replace(SCENARIO, kind=ScenarioKind.COMBINED),
        lambda: replace(SCENARIO, parents=("a",)),
        lambda: HistoricalObservation("fx", MOVE.factor, 1.0, 1.1, "wrong"),
        lambda: combine("combined", (SCENARIO,), "description"),
        lambda: combine("combined", (SCENARIO, SCENARIO), "description"),
        lambda: historical_scenario("history", (), None, None, "source", "description"),
    ],
)
def test_stress_provenance_guards(factory):
    with pytest.raises(ParallaxError):
        factory()


@pytest.mark.parametrize(
    "changes",
    [
        {"times": (0.0, 1.0)},
        {"times": (1.0, 1.0)},
        {"observed": (0.1,)},
        {"observed": (0.1, 1.0)},
        {"scales": (0.0, 0.01)},
    ],
)
def test_flat_probability_calibration_guards(changes):
    from parallax_risk.domain.validation.benchmark import FlatHazardProbabilityProblem

    original = FlatHazardProbabilityProblem((0.5, 1.0), (0.1, 0.2), (0.01, 0.01), "Synthetic test")
    with pytest.raises(ParallaxError):
        replace(original, **changes)
    with pytest.raises(ParallaxError):
        original.predict((-0.1,))


@pytest.mark.parametrize(
    "estimate",
    [
        replace(ESTIMATE, standard_error=0.0),
        replace(ESTIMATE, interval_method="unsupported"),
        replace(ESTIMATE, confidence_interval=(0.99, 1.01)),
        replace(ESTIMATE, sampling_unit="antithetic_pair"),
    ],
)
def test_forged_estimate_precision_is_rejected(estimate):
    with pytest.raises(ParallaxError):
        ConvergencePoint(2.0, estimate, CASE.hash)
