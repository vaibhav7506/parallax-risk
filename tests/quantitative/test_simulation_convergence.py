import pytest

from parallax_risk.application.simulation_examples import (
    convergence_experiment,
    moment_experiment,
    variance_experiment,
)


def test_seeded_monte_carlo_rate_and_sobol_comparison():
    experiment = convergence_experiment(counts=(256, 1024, 4096, 16384), replicates=32)
    # Empirical slope across independent replicates, broad declared statistical range.
    assert -0.75 < experiment.pseudo.log_rmse_slope < -0.25
    assert (
        experiment.sobol.rows[-1].root_mean_square_error
        < experiment.pseudo.rows[-1].root_mean_square_error / 5
    )
    assert experiment.sobol.log_rmse_slope < -0.6
    for study in (experiment.pseudo, experiment.sobol):
        assert study.nested_prefixes
        assert all(row.total_paths == 32 * row.paths_per_replicate for row in study.rows)
    result = experiment.sobol_inference.estimate
    assert result.independent_units == 32
    assert abs(result.mean - experiment.reference_call_expectation) < 6 * result.standard_error


def test_antithetic_and_control_effectiveness_reports_pilot_cost():
    result = variance_experiment(paths=16384, pilot_paths=2048)
    plain, paired, controlled = result.cases
    assert plain.pilot_paths == paired.pilot_paths == 0
    assert controlled.pilot_paths == 2048
    assert paired.variance_gain_against_plain > 1.5
    assert controlled.variance_gain_against_plain > 4
    assert controlled.work_adjusted_gain_against_plain < controlled.variance_gain_against_plain
    assert paired.result.estimate.independent_units == 8192
    assert result.pilot_control.pilot_key != plain.result.metadata.sequence.key


def test_production_moment_experiment_has_explicit_analytical_references():
    result = moment_experiment(paths=16384)
    for simulation, mean, variance in (
        (result.gbm, result.gbm_reference_mean, result.gbm_reference_variance),
        (result.vasicek, result.vasicek_reference_mean, result.vasicek_reference_variance),
    ):
        assert abs(simulation.raw_mean - mean) < 6 * simulation.estimate.standard_error
        assert simulation.raw_descriptive_variance == pytest.approx(variance, rel=0.05)
    assert result.is_synthetic
