"""Actual SciPy fits: parameter recovery, stability, residual lineage and failures."""

from dataclasses import replace

import numpy as np
import pytest

from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.domain.calibration.contracts import (
    CalibrationSettings,
    CalibrationStatus,
)
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from tests.fixtures.stochastic import heston_problem, hull_white_problem, vasicek_problem


@pytest.mark.parametrize(
    "factory,tolerance",
    [(vasicek_problem, 3e-6), (hull_white_problem, 2e-7), (heston_problem, 3e-5)],
)
def test_generated_parameter_recovery_and_repeatability(factory, tolerance):
    problem, bounds, truth = factory()
    solver = ScipyLeastSquares()
    result = solver.solve(problem, bounds, CalibrationSettings(), CalibrationRunId("recovery"))
    result.require_converged()
    assert result.status == CalibrationStatus.CONVERGED
    assert result.fitted_parameters == pytest.approx(truth, abs=tolerance, rel=0)
    assert result.rmse < 1e-8
    assert result.input_data_hash == problem.input_hash
    assert result.model_version == "0.3.0"
    assert tuple(name for name, _ in result.parameter_set) == problem.parameter_names
    assert result.objective_evaluations > result.optimizer_evaluations
    assert result.uncertainty.jacobian_rank == len(bounds)
    assert result.uncertainty.unavailable_reason is None
    assert result.uncertainty.covariance is not None
    replay = solver.solve(problem, bounds, CalibrationSettings(), CalibrationRunId("recovery"))
    assert replay == result


def test_alternative_initialization_and_quote_perturbation_stability():
    problem, bounds, truth = vasicek_problem()
    initial = (0.8, 0.08, 0.04)
    alternative = tuple(replace(b, initial=x) for b, x in zip(bounds, initial, strict=True))
    result = ScipyLeastSquares().solve(
        problem, alternative, CalibrationSettings(), CalibrationRunId("alternative")
    )
    result.require_converged()
    assert result.fitted_parameters == pytest.approx(truth, abs=3e-6, rel=0)
    points = tuple(
        replace(p, value=p.value + (1 if i % 2 else -1) * 1e-7)
        for i, p in enumerate(problem.observations)
    )
    noisy = replace(problem, observations=points)
    changed = ScipyLeastSquares().solve(
        noisy, bounds, CalibrationSettings(), CalibrationRunId("perturbed")
    )
    changed.require_converged()
    assert changed.fitted_parameters == pytest.approx(truth, abs=3e-4, rel=0)
    assert changed.input_data_hash != result.input_data_hash and changed.rmse > 0
    assert np.all(np.asarray(changed.uncertainty.standard_errors) > 0)
    assert np.linalg.eigvalsh(changed.uncertainty.covariance)[0] >= -1e-18


def test_optimizer_budget_failure_is_an_explicit_result():
    problem, bounds, _ = vasicek_problem()
    result = ScipyLeastSquares().solve(
        problem, bounds, CalibrationSettings(max_evaluations=1), CalibrationRunId("budget")
    )
    assert result.status == CalibrationStatus.FAILED and result.optimizer_status == 0
    assert result.rmse > 0 and result.optimizer_evaluations == 1
    assert result.uncertainty.unavailable_reason == "optimizer_did_not_converge"
    from parallax_risk.common.errors import CalibrationError

    with pytest.raises(CalibrationError, match="did not converge"):
        result.require_converged()


def test_active_bound_and_rank_deficient_uncertainty_are_not_invented():
    problem, bounds, _ = vasicek_problem()
    constrained = (replace(bounds[0], initial=0.1, upper=0.15), *bounds[1:])
    result = ScipyLeastSquares().solve(
        problem, constrained, CalibrationSettings(), CalibrationRunId("bound")
    )
    assert result.status == CalibrationStatus.CONVERGED and any(result.active_bounds)
    assert result.uncertainty.unavailable_reason == "active_parameter_bounds"
    assert result.uncertainty.covariance is None
    # An underdetermined set cannot identify all three parameters.
    small = replace(problem, observations=problem.observations[:1])
    under = ScipyLeastSquares().solve(
        small, bounds, CalibrationSettings(), CalibrationRunId("under")
    )
    under.require_converged()
    assert under.uncertainty.jacobian_rank < 3
    assert under.uncertainty.unavailable_reason == "rank_deficient_jacobian"


def test_weighted_and_unweighted_metrics_and_configuration_hash():
    problem, bounds, _ = vasicek_problem()
    scaled = replace(
        problem, observations=tuple(replace(p, scale=0.01) for p in problem.observations)
    )
    result = ScipyLeastSquares().solve(
        scaled, bounds, CalibrationSettings(max_evaluations=1), CalibrationRunId("weights")
    )
    assert result.scaled_rmse == pytest.approx(result.rmse / 0.01, abs=1e-13)
    assert result.scaled_residuals == pytest.approx(
        tuple(r / 0.01 for r in result.residuals), abs=1e-13
    )
    assert result.maximum_absolute_residual == max(abs(r) for r in result.residuals)
    assert all(
        p - o == r
        for p, o, r in zip(result.predictions, scaled.observed, result.residuals, strict=True)
    )
    different = ScipyLeastSquares().solve(
        scaled, bounds, CalibrationSettings(max_evaluations=2), CalibrationRunId("weights")
    )
    assert different.configuration_hash != result.configuration_hash
