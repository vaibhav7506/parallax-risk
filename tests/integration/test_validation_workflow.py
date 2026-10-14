"""Actual exposure/XVA repricing, paired observations, path/grid convergence and stresses."""

from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from parallax_risk.application.validation import calibration_band
from parallax_risk.application.validation_models import ProductionXvaModel
from parallax_risk.application.validation_stress import (
    HistoricalObservation,
    ScenarioKind,
    StressScenario,
    combine,
    historical_scenario,
    stress,
)
from parallax_risk.application.xva_revaluation import FactorMove
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.calibration.contracts import CalibrationSettings
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.random import SequenceKind
from parallax_risk.domain.validation.checks import ConvergenceAxis
from parallax_risk.domain.validation.contracts import Tolerance
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from tests.fixtures.stochastic import vasicek_problem
from tests.fixtures.xva import experiment, revaluation


def resized(case, count):
    request = replace(case.request, path_count=count)
    return replace(case, request=request, markets=replace(case.markets, request=request))


def finer(case):
    old = case.markets.dates
    dates = tuple(sorted(set(old) | {a + (b - a) // 2 for a, b in zip(old, old[1:], strict=False)}))
    times = tuple(year_fraction(dates[0], d, DayCount.ACT_365_FIXED) for d in dates)
    request = replace(case.request, grid=TimeGrid(times))
    margins = tuple(
        replace(m, times=times, posted_initial_margin=(m.posted_initial_margin[0],) * len(times))
        for m in case.margins
    )
    return replace(
        case,
        request=request,
        markets=replace(case.markets, request=request, dates=dates),
        margins=margins,
    )


def test_actual_model_outputs_and_path_cva_reconcile():
    inputs = experiment(16)
    model = ProductionXvaModel(revaluation())
    result = model.evaluate(inputs)
    observations = model.observations(inputs, "CVA")
    assert result.case_hash == inputs.hash
    assert result.metric("CVA").value == pytest.approx(np.mean(observations.values), abs=1e-12)
    assert result.metric("TOTAL").value == pytest.approx(
        sum(c.value for c in result.metric("TOTAL").contributions), abs=1e-12
    )
    paired_request = replace(
        inputs.request, sequence=replace(inputs.request.sequence, antithetic=True)
    )
    paired = replace(
        inputs, request=paired_request, markets=replace(inputs.markets, request=paired_request)
    )
    data = model.observations(paired, "CVA")
    assert (
        len(data.values) == 8 and data.total_paths == 16 and data.sampling_unit == "antithetic_pair"
    )
    assert np.mean(data.values) == pytest.approx(
        model.evaluate(paired).metric("CVA").value, abs=1e-12
    )
    assert model.observations(inputs, "EPE").values != data.values


def test_actual_path_and_time_step_studies_report_sampling_precision():
    inputs = experiment(16)
    model = ProductionXvaModel(revaluation())
    study = model.convergence(
        (inputs, resized(inputs, 32)),
        "CVA",
        ConvergenceAxis.PATH_COUNT,
        Tolerance(100),
        Tolerance(100),
        "Run exact retained cases",
    )
    assert study.passed and [p.estimate.total_paths for p in study.points] == [16, 32]
    assert study.points[-1].estimate.standard_error > 0
    strict = model.convergence(
        (inputs, resized(inputs, 32)),
        "CVA",
        ConvergenceAxis.PATH_COUNT,
        Tolerance(0),
        Tolerance(0),
        "Run exact retained cases",
    )
    assert not strict.passed and strict.precision_check.finding is not None
    grid = model.convergence(
        (inputs, finer(inputs)),
        "EPE",
        ConvergenceAxis.TIME_STEP,
        Tolerance(100),
        Tolerance(100),
        "Run declared grids",
    )
    assert grid.points[1].resolution < grid.points[0].resolution
    assert grid.points[0].estimate.total_paths == grid.points[1].estimate.total_paths == 16
    assert "bias" in grid.interpretation


def test_actual_hypothetical_combined_and_sourced_historical_adapter():
    inputs = experiment(8)
    model = ProductionXvaModel(revaluation())
    fx = RiskFactor(FactorKind.FX, "fx")
    recovery = RiskFactor(FactorKind.RECOVERY, "synthetic-cp")
    first = StressScenario(
        "spot-up",
        ScenarioKind.HYPOTHETICAL,
        (FactorMove("spot", fx, 0.1),),
        "Synthetic test parameters",
        "Direct FX spot shift",
    )
    second = StressScenario(
        "recovery-down",
        ScenarioKind.HYPOTHETICAL,
        (FactorMove("recovery", recovery, -0.1),),
        "Synthetic test parameters",
        "Recovery shift at fixed hazard",
    )
    combined = combine("combined", (first, second), "Ordered spot then recovery")
    values = stress(model, inputs, (first, second, combined))
    changed = model.workflow.bump(model.workflow.bump(inputs, fx, 0.1), recovery, -0.1)
    assert values[-1].stressed == model.evaluate(changed)
    assert values[-1].changes[0].value == pytest.approx(
        values[-1].stressed.metric("CVA").value - values[-1].baseline.metric("CVA").value, abs=1e-12
    )
    assert len(combined.parents) == 2
    # Adapter test data are explicitly synthetic; not claimed to be observed market history.
    historical = historical_scenario(
        "adapter-contract",
        (HistoricalObservation("spot", fx, 1.0, 1.1, "direct_quote_per_base"),),
        date(2020, 1, 1),
        date(2020, 1, 2),
        "Synthetic adapter contract test; NOT observed market data",
        "Verify dated supplied-shock ingestion",
    )
    history_result = stress(model, inputs, (historical,))[0]
    assert historical.moves[0].amount == pytest.approx(0.1, abs=1e-15)
    assert history_result.scenario.start_date == date(2020, 1, 1)
    with pytest.raises(ParallaxError):
        stress(model, inputs, (first,), maximum_evaluations=1)
    with pytest.raises(ParallaxError):
        stress(model, inputs, (first, first))


@pytest.mark.parametrize("kind", [1, 2])
def test_dependent_cva_samples_are_rejected(kind):
    with pytest.raises(ParallaxError, match="independent credit"):
        ProductionXvaModel(revaluation()).observations(experiment(8, kind), "CVA")


def test_observation_and_convergence_guards():
    model, inputs = ProductionXvaModel(revaluation()), experiment(8)
    for metric in ("TOTAL", "PFE"):
        with pytest.raises(ParallaxError):
            model.observations(inputs, metric)
    request = replace(
        inputs.request, sequence=replace(inputs.request.sequence, kind=SequenceKind.SOBOL)
    )
    sobol = replace(inputs, request=request, markets=replace(inputs.markets, request=request))
    with pytest.raises(ParallaxError, match="Sobol"):
        model.observations(sobol, "CVA")
    changed = model.workflow.bump(inputs, RiskFactor(FactorKind.FX, "fx"), 0.1)
    cases = [(inputs,), (inputs, changed), (inputs, finer(inputs)), (inputs, resized(inputs, 16))]
    axes = [
        ConvergenceAxis.PATH_COUNT,
        ConvergenceAxis.PATH_COUNT,
        ConvergenceAxis.PATH_COUNT,
        ConvergenceAxis.TIME_STEP,
    ]
    for ladder, axis in zip(cases, axes, strict=True):
        with pytest.raises(ParallaxError):
            model.convergence(ladder, "CVA", axis, Tolerance(1), Tolerance(1), "run")


def test_unavailable_or_constrained_calibration_covariance_is_not_invented():
    problem, bounds, _ = vasicek_problem()
    result = ScipyLeastSquares().solve(
        problem, bounds, CalibrationSettings(), CalibrationRunId("lab")
    )
    for bad in (
        replace(result, active_bounds=(1, 0, 0)),
        replace(result, uncertainty=replace(result.uncertainty, covariance=None)),
    ):
        with pytest.raises(ParallaxError, match="unavailable or constrained"):
            calibration_band(bad, lambda parameters: None, "CVA", (0.001,) * 3, ("rate",) * 3)


def test_complete_synthetic_lab_keeps_failures_and_replays():
    import json
    import subprocess
    import sys
    from pathlib import Path

    from parallax_risk.application.validation_examples import example, refined_case
    from parallax_risk.application.validation_models import ProductionCvaModel
    from parallax_risk.common.enums import Currency
    from parallax_risk.domain.validation.benchmark import (
        CvaBenchmarkCase,
        FlatHazardProbabilityProblem,
    )

    result = example(ScipyLeastSquares(), 8)
    assert len(result.invariants) == 5 and all(c.passed for c in result.invariants)
    assert len(result.stresses) == 3
    assert result.calibration_cva.upper > result.calibration_cva.lower
    assert result.bootstrap_cva.draws
    assert result.baseline.case_hash == result.xva_inputs.hash
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(root / "scripts/demo_validation.py")]
    first = subprocess.run(command, cwd=root, capture_output=True, check=True, timeout=90)
    second = subprocess.run(command, cwd=root, capture_output=True, check=True, timeout=90)
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["project"] == "Parallax Risk" and payload["is_synthetic"] is True
    assert payload["model_approval"] is False and payload["release"] == "0.9.0"
    changed = replace(
        result.xva_inputs,
        margins=(
            replace(result.xva_inputs.margins[0], posted_initial_margin=(1.0, 2.0, 3.0, 4.0)),
        ),
    )
    with pytest.raises(ParallaxError, match="constant"):
        refined_case(changed)
    # Propagate an actual fitted credit parameter into an actual production CVA metric.
    problem = FlatHazardProbabilityProblem(
        (0.5, 1.0, 2.0), (0.095, 0.182, 0.329), (0.01,) * 3, "Synthetic test probabilities"
    )
    from parallax_risk.domain.calibration.contracts import ParameterBound

    fitted = ScipyLeastSquares().solve(
        problem,
        (ParameterBound("hazard", 0.1, 0.0, 1.0),),
        CalibrationSettings(),
        CalibrationRunId("credit-band"),
    )
    case = CvaBenchmarkCase((0.0, 1.0), (100.0, 100.0), Currency.USD, 0.0, 0.2, 0.4)
    model = ProductionCvaModel()

    def revalue(parameters):
        return model.evaluate(replace(case, hazard=parameters[0]))

    with pytest.raises(ParallaxError, match="bounds"):
        calibration_band(fitted, revalue, "CVA", (2.0,), ("hazard",))
    with pytest.raises(ParallaxError, match="resolution"):
        calibration_band(
            fitted, lambda parameters: model.evaluate(case), "CVA", (1e-4,), ("hazard",)
        )
    with pytest.raises(ParallaxError):
        calibration_band(fitted, revalue, "CVA", (1e-4, 1e-4), ("hazard",))
    with pytest.raises(ParallaxError):
        calibration_band("bad", revalue, "CVA", (1e-4,), ("hazard",))
