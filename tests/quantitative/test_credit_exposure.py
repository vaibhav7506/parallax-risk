"""Independent mathematical targets and explicit dependence/monotonicity scope."""

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError, NumericalError
from parallax_risk.domain.credit.dependence import (
    ReducedFormSpread,
    conditional_survival,
    default_thresholds,
    intensity_default_times,
    static_rank_thresholds,
)
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import (
    compare_dependence,
    exposure_at_default,
    profile,
)
from parallax_risk.domain.simulation.random import StreamKey


def test_dynamic_market_credit_dependence_and_default_distribution():
    from dataclasses import replace
    from datetime import date

    from parallax_risk.domain.models.correlation import CorrelationMatrix
    from parallax_risk.domain.simulation.engine import MonteCarloEngine
    from tests.fixtures.exposure import fx_request

    dates = (date(2025, 1, 1), date(2025, 4, 1), date(2025, 7, 1), date(2025, 10, 1))
    req = fx_request(paths=20000, batch=20000, dates=dates, spread_vol=1.0)
    matrix = tuple(
        tuple(1.0 if i == j else 0.8 if {i, j} == {2, 3} else 0.0 for j in range(4))
        for i in range(4)
    )
    req = replace(
        req,
        correlation=CorrelationMatrix(
            tuple(n for c in req.components for n in c.factor_names), matrix
        ),
    )
    states = next(MonteCarloEngine().iter_batches(req)).values.array
    exposures = np.maximum(states[:, :, 2] - 1.1, 0) * 100
    hazards = states[:, :-1, 3] / 0.6
    thresholds = default_thresholds(StreamKey(42, 1), req.path_count)
    dependent = exposure_at_default(
        exposures, req.grid.times, intensity_default_times(req.grid.times, hazards, thresholds)
    )
    # Independently permute entire credit histories: preserves the intensity marginal,
    # and hence every conditional-survival average, while breaking market dependence.
    permutation = np.random.Generator(np.random.PCG64DXSM(99)).permutation(req.path_count)
    independent = exposure_at_default(
        exposures,
        req.grid.times,
        intensity_default_times(req.grid.times, hazards[permutation], thresholds),
    )
    assert dependent.mean_with_nondefault_zero > independent.mean_with_nondefault_zero * 1.15
    pd = 1 - conditional_survival(req.grid.times, hazards)[:, -1].mean()
    assert abs(dependent.default_probability - pd) < 6 * math.sqrt(pd * (1 - pd) / req.path_count)
    assert conditional_survival(req.grid.times, hazards[permutation]).mean(axis=0) == pytest.approx(
        conditional_survival(req.grid.times, hazards).mean(axis=0), abs=1e-14
    )


def test_piecewise_survival_inversion_and_small_probability():
    curve = PiecewiseHazardCurve((0.0, 1.0, 2.0, 4.0), (0.0, 0.2, 0.5))
    assert curve.cumulative_hazard(0) == 0 and curve.cumulative_hazard(1) == 0
    assert curve.cumulative_hazard(3) == pytest.approx(0.7, abs=1e-15)
    assert curve.survival(3) == pytest.approx(math.exp(-0.7), rel=1e-15)
    assert curve.default_probability(3) + curve.survival(3) == pytest.approx(1, abs=1e-15)
    assert curve.default_increment(2, 3) == pytest.approx(
        math.exp(-0.2) - math.exp(-0.7), abs=1e-15
    )
    assert curve.default_time(0.1) == pytest.approx(1.5, abs=1e-15)
    assert curve.default_time(0.7) == pytest.approx(3, abs=1e-15)
    assert curve.default_time(1.2) == pytest.approx(4, abs=1e-15)
    assert curve.default_time(1.21) is None
    assert PiecewiseHazardCurve((0.0, 1.0), (1e-16,)).default_probability(1) == pytest.approx(
        1e-16, rel=1e-15
    )
    assert PiecewiseHazardCurve((0.0, 1.0), (1000.0,)).survival(1) == 0
    assert curve.hash != PiecewiseHazardCurve(curve.times, (0.0, 0.2, 0.6)).hash
    with pytest.raises(DomainValidationError, match="resolution"):
        PiecewiseHazardCurve((0.0, 1.0), (1e300,)).default_time(1e-300)


@pytest.mark.parametrize(
    "times,hazards",
    [
        ((), ()),
        ((0.0,), ()),
        ((0.0, 1.0), ()),
        ((1.0, 2.0), (0.1,)),
        ((0.0, 0.0), (0.1,)),
        ((0.0, float("nan")), (0.1,)),
        ((0.0, 1.0), (-0.1,)),
        ((0.0, 1.0), (True,)),
        ([0.0, 1.0], (0.1,)),
        ((0.0, 1.0), [0.1]),
        ((0.0, 2.0), (1e308,)),
    ],
)
def test_invalid_hazard(times, hazards):
    with pytest.raises((DomainValidationError, NumericalError)):
        PiecewiseHazardCurve(times, hazards)


def test_curve_range_recovery_and_credit_triangle():
    curve = PiecewiseHazardCurve((0.0, 1.0), (0.0,))
    assert curve.default_time(1) is None and curve.default_probability(1) == 0
    for time in (-1, 2, float("nan")):
        with pytest.raises((DomainValidationError, NumericalError)):
            curve.survival(time)
    for threshold in (0, -1, float("inf"), True):
        with pytest.raises((DomainValidationError, NumericalError)):
            curve.default_time(threshold)
    with pytest.raises((DomainValidationError, NumericalError)):
        curve.default_increment(1, 0)
    assert RecoveryAssumption(0).loss_given_default == 1
    assert RecoveryAssumption(1).loss_given_default == 0
    for recovery in (-0.1, 1.1, float("nan"), True):
        with pytest.raises((DomainValidationError, NumericalError)):
            RecoveryAssumption(recovery)
    policy = ReducedFormSpread(RecoveryAssumption(0.4))
    assert policy.intensity(0.012) == pytest.approx(0.02, rel=1e-15)
    assert len(policy.hash) == 64
    with pytest.raises((DomainValidationError, NumericalError)):
        policy.intensity(-1)
    for recovery in (None, RecoveryAssumption(1)):
        with pytest.raises((DomainValidationError, NumericalError)):
            ReducedFormSpread(recovery)


def test_simulated_default_cdf_matches_piecewise_survival():
    curve = PiecewiseHazardCurve((0.0, 1.0, 2.0), (0.1, 0.4))
    thresholds = default_thresholds(StreamKey(987, 1), 50000)
    times = tuple(curve.default_time(float(e)) for e in thresholds)
    for endpoint in (0.5, 1, 1.5, 2):
        expected = curve.default_probability(endpoint)
        empirical = sum(t is not None and t <= endpoint for t in times) / len(times)
        tolerance = 6 * math.sqrt(expected * (1 - expected) / len(times))
        assert abs(empirical - expected) < tolerance
    np.testing.assert_array_equal(thresholds, default_thresholds(StreamKey(987, 1), 50000))
    assert not np.array_equal(thresholds, default_thresholds(StreamKey(987, 2), 50000))


def test_dynamic_integration_left_constant_not_terminal_lookahead():
    intensity = np.array([[0.0, 2.0], [1.0, 0.0]], dtype=np.float64)
    thresholds = np.array([1.0, 0.25], dtype=np.float64)
    assert intensity_default_times((0.0, 1.0, 2.0), intensity, thresholds) == (1.5, 0.25)
    with pytest.raises((DomainValidationError, NumericalError)):
        intensity_default_times((0.0, 1.0), intensity, thresholds)
    with pytest.raises((DomainValidationError, NumericalError)):
        default_thresholds(None, 2)
    with pytest.raises((DomainValidationError, NumericalError)):
        default_thresholds(StreamKey(1), 0)


def test_static_rank_stress_preserves_default_marginal_and_raises_conditioned_exposure():
    n = 20000
    key = StreamKey(981, 1)
    e = default_thresholds(key, n)
    score = StreamKey(981, 0).generator().lognormal(0, 1, n)
    values = np.repeat(score[:, None], 2, axis=1).astype(np.float64)
    curve = PiecewiseHazardCurve((0.0, 1.0), (0.3,))
    baseline = exposure_at_default(
        values, curve.times, tuple(curve.default_time(float(x)) for x in e)
    )
    stressed = static_rank_thresholds(e, score, 0.8, StreamKey(981, 2))
    np.testing.assert_array_equal(np.sort(e), np.sort(stressed))
    scenario = exposure_at_default(
        values, curve.times, tuple(curve.default_time(float(x)) for x in stressed)
    )
    result = compare_dependence(baseline, scenario)
    assert baseline.defaults == scenario.defaults
    assert result.ratio > 1.8 and scenario.mean_given_default > baseline.mean_given_default
    np.testing.assert_array_equal(static_rank_thresholds(e, score, 0, StreamKey(981, 2)), e)
    right_way = static_rank_thresholds(e, score, -1, StreamKey(981, 2))
    assert np.corrcoef(score, right_way)[0, 1] > 0
    assert np.all(np.isfinite(static_rank_thresholds(e, np.ones(n), 1, StreamKey(981, 2))))


@pytest.mark.parametrize("rho", [2, float("nan"), True])
def test_invalid_static_rho(rho):
    with pytest.raises((DomainValidationError, NumericalError)):
        static_rank_thresholds(np.ones(2), np.ones(2), rho, StreamKey(1))


def test_bad_static_shape_and_keys():
    for e, score, key in [
        (np.ones(2), np.ones(3), StreamKey(1)),
        (np.zeros(2), np.ones(2), StreamKey(1)),
        (np.ones(2), np.ones(2), None),
    ]:
        with pytest.raises((DomainValidationError, NumericalError)):
            static_rank_thresholds(e, score, 0.3, key)


def test_empirical_ee_ene_pfe_epe_with_known_nonmonotone_time_profile():
    pos = np.array([[0.0, 2.0, 0.0], [2.0, 4.0, 0.0]], dtype=np.float64)
    neg = np.array([[0.0, 0.0, 2.0], [0.0, 2.0, 4.0]], dtype=np.float64)
    result = profile(pos, neg, (0.0, 1.0, 3.0), (0.0, 0.5, 1.0), Currency.USD)
    assert result.expected_exposure == (1.0, 3.0, 0.0)
    assert result.expected_negative_exposure == (0.0, 1.0, 3.0)
    assert result.expected_positive_exposure == pytest.approx(5 / 3, rel=1e-15)
    np.testing.assert_array_equal(
        result.potential_future_exposure.array, np.array([[0, 2, 0], [1, 3, 0], [2, 4, 0]])
    )
    zero = profile(np.zeros((2, 3)), np.zeros((2, 3)), (0.0, 1.0, 3.0), (0.99,), Currency.USD)
    assert zero.expected_positive_exposure == 0
    ead = exposure_at_default(pos, (0.0, 1.0, 3.0), (0.25, None))
    assert ead.bucket_times == (1.0, None) and ead.positive_exposures == (2.0, 0.0)
    assert ead.defaults == 1 and ead.mean_given_default == 2 and ead.mean_with_nondefault_zero == 1
    no_default = exposure_at_default(pos, (0.0, 1.0, 3.0), (None, None))
    assert (
        no_default.mean_given_default is None
        and compare_dependence(no_default, no_default).ratio is None
    )


@given(
    st.lists(st.floats(min_value=0, max_value=10000, allow_nan=False), min_size=2, max_size=20),
    st.floats(0, 10000),
)
@settings(max_examples=60, deadline=None)
def test_pfe_quantile_and_pathwise_collateral_monotonicity(values, received):
    a = np.repeat(np.asarray(values, dtype=np.float64)[:, None], 2, axis=1)
    less = np.maximum(a - received, 0)
    first = profile(a, np.zeros_like(a), (0.0, 1.0), (0.5, 0.9, 0.99), Currency.USD)
    second = profile(less, np.zeros_like(a), (0.0, 1.0), (0.5, 0.9, 0.99), Currency.USD)
    assert np.all(np.diff(first.potential_future_exposure.array, axis=0) >= 0)
    assert np.all(
        second.potential_future_exposure.array <= first.potential_future_exposure.array + 1e-10
    )


@pytest.mark.parametrize(
    "times,qs",
    [
        ((), (0.9,)),
        ((0.0,), (0.9,)),
        ((1.0, 2.0), (0.9,)),
        ((0.0, 0.0), (0.9,)),
        ((0.0, float("inf")), (0.9,)),
        ((0.0, 1.0), ()),
        ((0.0, 1.0), (0.9, 0.8)),
        ((0.0, 1.0), (-0.1,)),
        ((0.0, 1.0), (1.1,)),
        ((0.0, 1.0), (True,)),
    ],
)
def test_invalid_profile_settings(times, qs):
    with pytest.raises((DomainValidationError, NumericalError)):
        profile(np.ones((2, len(times))), np.zeros((2, len(times))), times, qs, Currency.USD)


def test_bad_exposure_shapes_defaults_and_overflow():
    for pos, neg in [(np.ones((2, 2)), np.ones((1, 2))), (-np.ones((2, 2)), np.zeros((2, 2)))]:
        with pytest.raises((DomainValidationError, NumericalError)):
            profile(pos, neg, (0.0, 1.0), (0.9,), Currency.USD)
    with pytest.raises((DomainValidationError, NumericalError)):
        profile(np.full((2, 2), 1e308), np.zeros((2, 2)), (0.0, 1.0), (0.9,), Currency.USD)
    for defaults in [(), (0, None), (2, None), (float("nan"), None)]:
        with pytest.raises((DomainValidationError, NumericalError)):
            exposure_at_default(np.ones((2, 2)), (0.0, 1.0), defaults)
    with pytest.raises((DomainValidationError, NumericalError)):
        compare_dependence(None, None)
    small = exposure_at_default(np.ones((1, 2)), (0.0, 1.0), (None,))
    big = exposure_at_default(np.ones((2, 2)), (0.0, 1.0), (None, None))
    with pytest.raises((DomainValidationError, NumericalError)):
        compare_dependence(small, big)


def test_conditional_survival_and_invalid_intensity_inputs():
    intensities = np.array([[0.0, 2.0], [1.0, 0.0]], dtype=np.float64)
    result = conditional_survival((0.0, 1.0, 2.0), intensities)
    np.testing.assert_allclose(
        result, [[1, 1, math.exp(-2)], [1, math.exp(-1), math.exp(-1)]], rtol=1e-15
    )
    assert np.all(np.diff(result, axis=1) <= 0)
    assert conditional_survival((0.0, 1.0), np.array([[1000.0]]))[0, 1] == 0
    for times, array in [
        ((0.0, 1.0), intensities),
        ((0.0, 1.0, 2.0), -intensities),
        ((0.0, 2.0), np.array([[1e308]])),
        (None, intensities),
    ]:
        with pytest.raises(DomainValidationError):
            conditional_survival(times, array)
    with pytest.raises(DomainValidationError):
        intensity_default_times(None, intensities, np.ones(2))


def test_zero_sampler_output_is_rejected(monkeypatch):
    class ZeroGenerator:
        def exponential(self, size):
            return np.zeros(size, dtype=np.float64)

    monkeypatch.setattr(StreamKey, "generator", lambda self: ZeroGenerator())
    with pytest.raises(DomainValidationError):
        default_thresholds(StreamKey(42), 3)


def test_integrated_hazard_sum_overflow_rejected():
    with pytest.raises(DomainValidationError):
        PiecewiseHazardCurve((0.0, 1.0, 2.0), (1e308, 1e308))
