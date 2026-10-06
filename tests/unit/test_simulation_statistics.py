import math

import numpy as np
import pytest

from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.domain.simulation.controls import ControlVariate, fit_control
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.simulation.statistics import (
    OnlineMoments,
    independent_scramble_estimate,
    sampling_units,
)


def test_streaming_centered_moments_and_student_interval():
    values = np.asarray([1.0, 4.0, 2.0, 6.0, -1.0, 8.0])
    aggregate = OnlineMoments()
    for chunk in (values[:1], values[1:4], values[4:]):
        aggregate.update(chunk)
    estimate = aggregate.estimate(total_paths=6, sampling_unit="iid_path")
    assert estimate.mean == pytest.approx(np.mean(values))
    assert estimate.sample_variance == pytest.approx(np.var(values, ddof=1))
    assert estimate.standard_error == pytest.approx(np.std(values, ddof=1) / math.sqrt(6))
    assert estimate.confidence_interval[0] < estimate.mean < estimate.confidence_interval[1]
    assert estimate.independent_units == estimate.total_paths == 6
    assert "approximation" in estimate.interval_method


def test_high_offset_moments_do_not_subtract_large_raw_squares():
    values = 1e12 + np.arange(100.0)
    aggregate = OnlineMoments()
    aggregate.update(values[:50])
    aggregate.update(values[50:])
    assert aggregate.variance == pytest.approx(np.var(values, ddof=1), rel=1e-12)
    # A constant finite large value has zero variance; no spurious infinity*zero.
    aggregate = OnlineMoments()
    aggregate.update(np.asarray([1e200, 1e200]))
    assert aggregate.variance == 0


def test_moment_failure_does_not_corrupt_prior_accumulator():
    aggregate = OnlineMoments()
    aggregate.update(np.asarray([1.0, 2.0]))
    prior = (aggregate.count, aggregate.mean, aggregate.m2)
    with pytest.raises(NumericalError):
        aggregate.update(np.asarray([-1e308, 1e308]))
    assert (aggregate.count, aggregate.mean, aggregate.m2) == prior
    with pytest.raises(SimulationError):
        _ = OnlineMoments().variance


@pytest.mark.parametrize("confidence", [0, 1, -1, np.inf, np.nan, True])
def test_interval_rejects_bad_confidence(confidence):
    aggregate = OnlineMoments()
    aggregate.update(np.asarray([1.0, 2.0]))
    with pytest.raises((SimulationError, NumericalError)):
        aggregate.estimate(total_paths=2, sampling_unit="iid_path", confidence=confidence)


@pytest.mark.parametrize(
    "total,unit", [(1, "iid_path"), (3, "iid_path"), (3, "antithetic_pair"), (2, "wrong")]
)
def test_sampling_unit_and_counts_are_explicit(total, unit):
    aggregate = OnlineMoments()
    aggregate.update(np.asarray([1.0, 2.0]))
    with pytest.raises(SimulationError):
        aggregate.estimate(total_paths=total, sampling_unit=unit)


def test_antithetic_pair_averages_and_counterexample():
    key = StreamKey(234)
    normals = key.generator().standard_normal(50000)
    paired = np.empty(100000)
    paired[0::2], paired[1::2] = normals, -normals
    assert np.array_equal(sampling_units(paired, antithetic=True), np.zeros(50000))
    assert sampling_units(paired, antithetic=False) is paired
    # An even function duplicates each value: antithetics can worsen variance.
    squared_pairs = sampling_units(paired**2, antithetic=True)
    ordinary = key.generator().standard_normal(100000) ** 2
    pair_estimator_variance = np.var(squared_pairs, ddof=1) / 50000
    plain_estimator_variance = np.var(ordinary, ddof=1) / 100000
    assert pair_estimator_variance / plain_estimator_variance == pytest.approx(2.0, rel=0.06)
    with pytest.raises(SimulationError):
        sampling_units(paired, antithetic=1)
    with pytest.raises(SimulationError):
        sampling_units(np.asarray([1.0]), antithetic=True)


def test_scramble_inference_uses_replicates_not_individual_points():
    means = np.asarray([1.02, 0.98, 1.01, 0.99])
    result = independent_scramble_estimate(means, paths_per_replicate=1024)
    assert result.independent_units == 4
    assert result.total_paths == 4096
    assert result.sampling_unit == "independent_scramble"
    assert result.standard_error == pytest.approx(np.std(means, ddof=1) / 2)
    with pytest.raises(SimulationError):
        independent_scramble_estimate(means[:1], paths_per_replicate=1024)
    with pytest.raises(SimulationError):
        independent_scramble_estimate(means, paths_per_replicate=0)


def test_control_coefficient_is_frozen_from_separate_pilot():
    y = np.asarray([0.0, 1.0, 2.0, 3.0])
    x = 2 * y + 4
    pilot = StreamKey(1, 1)
    fitted = fit_control(x, y, known_mean=1.5, pilot_key=pilot, control_name="linear_control")
    assert fitted.coefficient == pytest.approx(2)
    adjusted = fitted.adjust(x, y, evaluation_key=StreamKey(1, 2))
    assert np.array_equal(adjusted, np.full(4, 7.0))
    with pytest.raises(SimulationError, match="different"):
        fitted.adjust(x, y, evaluation_key=pilot)
    with pytest.raises(SimulationError):
        fitted.adjust(x, y[:2], evaluation_key=StreamKey(1, 2))
    with pytest.raises(SimulationError):
        fitted.adjust(x, y, evaluation_key=4)


@pytest.mark.parametrize(
    "changes",
    [
        {"coefficient": np.inf},
        {"known_mean": np.nan},
        {"pilot_key": 4},
        {"pilot_observations": 1},
        {"control_name": " "},
    ],
)
def test_control_metadata_rejects_ambiguous_values(changes):
    data = {
        "coefficient": 1.0,
        "known_mean": 0.0,
        "pilot_key": StreamKey(1),
        "pilot_observations": 4,
        "control_name": "test",
    }
    with pytest.raises((SimulationError, NumericalError)):
        ControlVariate(**(data | changes))


@pytest.mark.parametrize(
    "target,control",
    [
        (np.asarray([1.0]), np.asarray([1.0])),
        (np.asarray([1.0, 2.0]), np.asarray([1.0])),
        (np.asarray([1.0, 2.0]), np.asarray([1.0, 1.0])),
        (np.asarray([1.0, 2.0]), np.asarray([1e-200, 2e-200])),
    ],
)
def test_control_pilot_rejects_insufficient_or_unresolved_variance(target, control):
    with pytest.raises(SimulationError):
        fit_control(target, control, known_mean=0, pilot_key=StreamKey(1), control_name="fixture")


def test_control_arithmetic_range_is_guarded():
    with pytest.raises(NumericalError):
        fit_control(
            np.asarray([-1e308, 1e308]),
            np.asarray([-1.0, 1.0]),
            known_mean=0,
            pilot_key=StreamKey(1),
            control_name="range",
        )
    model = ControlVariate(1e308, 0.0, StreamKey(1), 4, "range")
    with pytest.raises(NumericalError):
        model.adjust(np.asarray([1.0]), np.asarray([1e308]), evaluation_key=StreamKey(2))
