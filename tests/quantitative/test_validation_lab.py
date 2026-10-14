"""Independent analytical targets, production grid bias, statistical units and delta method."""

import math
from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import norm

from parallax_risk.application.validation import ValidationLab, calibration_band, perturbation_band
from parallax_risk.application.validation_invariants import cva_invariants
from parallax_risk.application.validation_models import ProductionCvaModel
from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.domain.calibration.contracts import CalibrationSettings
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase, IndependentCvaBenchmark
from parallax_risk.domain.validation.checks import equality, monotonicity, sensitivity
from parallax_risk.domain.validation.contracts import Contribution, Metric, ModelOutput, Tolerance
from parallax_risk.domain.validation.uncertainty import (
    IidUnitResampler,
    IndependentObservations,
    bootstrap,
    propagate_covariance,
)
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from tests.fixtures.stochastic import vasicek_problem

REPRO = (
    "Retain exact case hashes, source release and run "
    "pytest tests/quantitative/test_validation_lab.py"
)


def case(rate=0.0, hazard=0.2, recovery=0.4, points=2, exposure=100.0):
    times = tuple(float(t) for t in np.linspace(0.0, 2.0, points))
    return CvaBenchmarkCase(times, (exposure,) * points, Currency.USD, rate, hazard, recovery)


@pytest.mark.parametrize("rate", [0.0, 0.03, -0.02, -0.2])
@pytest.mark.parametrize("hazard", [0.0, 0.2])
@pytest.mark.parametrize("recovery", [0.0, 0.4, 1.0])
def test_analytical_constant_exposure(rate, hazard, recovery):
    inputs = case(rate, hazard, recovery)
    value = IndependentCvaBenchmark().evaluate(inputs).metric("CVA").value
    speed = rate + hazard
    integral = 2.0 if speed == 0 else (1 - math.exp(-speed * 2)) / speed
    expected = -(1 - recovery) * 100 * hazard * integral
    assert value == pytest.approx(expected, abs=1e-12, rel=2e-14)
    if rate == 0:
        production = ProductionCvaModel().evaluate(inputs).metric("CVA").value
        assert production == pytest.approx(expected, abs=1e-12, rel=2e-14)


def test_grid_bias_is_found_and_refinement_reduces_it():
    errors = []
    for points in (2, 5, 17, 65):
        comparison = ValidationLab(ProductionCvaModel(), IndependentCvaBenchmark()).compare(
            case(0.3, points=points), Tolerance(1e-6), REPRO
        )
        difference = comparison.differences[0]
        assert difference.check.passed is False
        assert difference.check.finding.affected_metric == "CVA"
        assert difference.check.finding.reproduction == REPRO
        assert difference.residual == 0
        assert difference.contributions[0].value == difference.difference
        errors.append(abs(difference.difference))
    assert all(a > b for a, b in zip(errors, errors[1:], strict=False))
    assert errors[-1] < errors[0] / 1000


def test_independent_linear_exposure_integral_closed_form():
    # E(t)=50t, D=1; integral t*h*exp(-h*t) dt, horizon=2.
    inputs = replace(case(), exposure=(0.0, 100.0))
    expected = -0.6 * 50 * ((1 - math.exp(-0.4)) / 0.2 - 2 * math.exp(-0.4))
    actual = IndependentCvaBenchmark().evaluate(inputs)
    assert actual.metric("CVA").value == pytest.approx(expected, abs=1e-11, rel=1e-12)
    assert "scipy_quad" in actual.assumptions[-1]


@pytest.mark.parametrize("inputs", [case(), case(0.1), case(-0.02), case(exposure=0.0)])
def test_automatic_zero_scaling_and_collateral_invariants(inputs):
    results = cva_invariants(ProductionCvaModel(), inputs, Tolerance(1e-12, 1e-12), REPRO)
    assert len(results) == 5 and all(c.passed for c in results)


def test_local_derivative_and_justified_recovery_monotonicity():
    model, inputs = ProductionCvaModel(), case()
    target = 100 * (1 - math.exp(-0.4))
    result = sensitivity(
        lambda bump: model.evaluate(replace(inputs, recovery=0.4 + bump)).metric("CVA"),
        0.01,
        "recovery_fraction",
        Tolerance(1e-9),
        evidence=(inputs.hash,),
        reproduction=REPRO,
        version="0.9.0",
        expected_derivative=target,
    )
    assert result.consistency.passed and result.reference.passed
    assert result.derivative == pytest.approx(target, abs=1e-10)
    assert "per recovery_fraction" in result.derivative_unit
    values = tuple(
        model.evaluate(replace(inputs, recovery=r)).metric("CVA") for r in (0.0, 0.4, 1.0)
    )
    assert monotonicity(
        "recovery-increasing",
        values,
        increasing=True,
        tolerance=Tolerance(1e-12),
        evidence=(inputs.hash,),
        reproduction=REPRO,
        version="0.9.0",
    ).passed
    failed = monotonicity(
        "wrong-direction",
        values,
        increasing=False,
        tolerance=Tolerance(1e-12),
        evidence=(inputs.hash,),
        reproduction=REPRO,
        version="0.9.0",
    )
    assert not failed.passed and failed.finding.status == "open"


def test_finite_difference_inconsistency_is_a_finding():
    result = sensitivity(
        lambda x: Metric("cube", x**3, "USD"),
        0.1,
        "unit",
        Tolerance(1e-8),
        evidence=("Cubic mathematical target",),
        reproduction=REPRO,
        version="synthetic",
    )
    assert result.derivative == pytest.approx(0.01, abs=1e-15)
    assert result.half_bump_derivative == pytest.approx(0.0025, abs=1e-15)
    assert not result.consistency.passed and result.reference is None
    assert equality(
        "boundary",
        Metric("value", 1.0, "USD"),
        0.0,
        Tolerance(1.0),
        evidence=("boundary",),
        reproduction=REPRO,
        version="synthetic",
    ).passed


def test_bootstrap_replay_owned_units_and_constant_statistic():
    data = IndependentObservations(
        "CVA", "USD", (-1.0, -3.0, -2.0, -4.0), "antithetic_pair", 8, "a" * 64
    )
    key = StreamKey(124, 6, 3)
    kwargs = {"statistic_name": "mean", "replicates": 100, "confidence": 0.9}

    def statistic(values):
        return math.fsum(values) / len(values)

    first = bootstrap(data, key, IidUnitResampler(), statistic, **kwargs)
    assert bootstrap(data, key, IidUnitResampler(), statistic, **kwargs) == first
    assert first.lower <= -2.5 <= first.upper and first.center == -2.5
    other = bootstrap(data, StreamKey(125, 6, 3), IidUnitResampler(), statistic, **kwargs)
    assert other.draws != first.draws
    constant = replace(data, values=(-2.0,) * 4)
    band = bootstrap(constant, key, IidUnitResampler(), statistic, **kwargs)
    assert band.lower == band.upper == band.center == -2
    # Independent address draws are order-independent.
    resampler = IidUnitResampler()
    later = resampler.resample(data.values, key, 9)
    resampler.resample(data.values, key, 0)
    assert later == resampler.resample(data.values, key, 9)


def test_delta_method_includes_covariance_and_units():
    metric = Metric("CVA", -20.0, "USD")
    covariance = ((4.0, 1.0), (1.0, 9.0))
    band = propagate_covariance(
        metric, (2.0, -3.0), covariance, ("decimal_rate", "recovery_fraction"), "b" * 64
    )
    variance = 4 * 4 + 9 * 9 - 12
    width = norm.isf(0.025) * math.sqrt(variance)
    assert (band.lower, band.upper) == pytest.approx((-20 - width, -20 + width), abs=1e-12)
    assert band.unit == "USD" and "local_linear" in band.method
    zero = propagate_covariance(metric, (0.0,), ((0.0,),), ("rate",), "b" * 64)
    assert zero.lower == zero.upper == -20


def test_actual_parameter_ensemble_is_not_a_confidence_law():
    inputs = case()
    scenarios = tuple(replace(inputs, recovery=x) for x in (0.2, 0.4, 0.6))
    band = perturbation_band(ProductionCvaModel(), inputs, scenarios, "CVA", confidence=0.8)
    values = [ProductionCvaModel().evaluate(c).metric("CVA").value for c in scenarios]
    assert (band.lower, band.upper) == pytest.approx(np.quantile(values, (0.1, 0.9)), abs=1e-12)
    assert "not_confidence_interval" in band.method


def test_real_calibration_covariance_propagation():
    problem, bounds, _ = vasicek_problem()
    fitted = ScipyLeastSquares().solve(
        problem, bounds, CalibrationSettings(), CalibrationRunId("lab")
    )

    def revalue(parameters):
        from parallax_risk.common.canonical import content_hash

        # Independent selected linear risk functional; units USD per declared parameter.
        value = 2 * parameters[0] - 3 * parameters[1] + 4 * parameters[2]
        return ModelOutput(
            content_hash(parameters),
            "linear-risk-target",
            "synthetic",
            (Metric("risk", value, "USD", (Contribution("linear", value),)),),
            content_hash(value),
            ("Synthetic linear risk functional of an actual calibration",),
        )

    band = calibration_band(fitted, revalue, "risk", (1e-4,) * 3, ("speed", "level", "volatility"))
    gradient = np.array([2.0, -3.0, 4.0])
    variance = gradient @ np.asarray(fitted.uncertainty.covariance) @ gradient
    expected_width = norm.isf(0.025) * math.sqrt(variance)
    assert band.upper - band.center == pytest.approx(expected_width, abs=1e-15, rel=1e-6)
