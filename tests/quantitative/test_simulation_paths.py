import math
from dataclasses import replace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import kstest

from parallax_risk.common.errors import ModelError, NumericalError, SimulationError
from parallax_risk.domain.models.assets import GeometricBrownianMotion, Heston
from parallax_risk.domain.models.base import ou_loading
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.discretization import (
    EulerMaruyama,
    ExactTransition,
    HestonProjectedEuler,
)
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve, Vasicek
from parallax_risk.domain.simulation.analytics import gbm_call_expectation, gbm_terminal_moments
from parallax_risk.domain.simulation.contracts import Scheme, TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine, innovation_correlation
from parallax_risk.domain.simulation.kernels import step_batch
from parallax_risk.domain.simulation.random import (
    NormalStream,
    SequenceKind,
    SequenceSpec,
    StreamKey,
)
from tests.fixtures.simulation import component, request


def paths(config):
    return np.concatenate([batch.values.array for batch in MonteCarloEngine().iter_batches(config)])


@pytest.mark.parametrize(
    "model,state,scheme",
    [
        (GeometricBrownianMotion(0.04, 0.2), (100.0,), Scheme.EXACT),
        (GeometricBrownianMotion(0.04, 0.2), (100.0,), Scheme.EULER),
        (Vasicek(0.3, 0.04, 0.01), (-0.01,), Scheme.EXACT),
        (Vasicek(0.3, 0.04, 0.01), (-0.01,), Scheme.EULER),
        (HullWhite(0.3, 0.01, LinearForwardCurve(0.03, 0.002)), (0.03,), Scheme.EXACT),
        (HullWhite(0.3, 0.01, LinearForwardCurve(0.03, 0.002)), (0.03,), Scheme.EULER),
        (Heston(1.5, 0.04, 0.3, -0.6, 0.03), (100.0, 0.04), Scheme.EULER),
        (Heston(1.5, 0.04, 0.3, -0.6, 0.03), (100.0, 0.04), Scheme.HESTON_PROJECTED),
    ],
)
def test_vectorized_transitions_match_scalar_contracts(model, state, scheme):
    item = component(model, state=state, scheme=scheme)
    shocks = np.tile(np.asarray([[-0.15], [0.0], [0.15]]), (1, model.driver_dimension))
    states = np.tile(np.asarray(state), (3, 1))
    strategies = {
        Scheme.EXACT: ExactTransition(),
        Scheme.EULER: EulerMaruyama(),
        Scheme.HESTON_PROJECTED: HestonProjectedEuler(),
    }
    vectorized, count = step_batch(item, 0.4, states, 0.1, shocks)
    scalar = np.asarray(
        [strategies[scheme].step(model, 0.4, state, 0.1, tuple(row)) for row in shocks]
    )
    assert np.allclose(vectorized, scalar, rtol=1e-13, atol=1e-13)
    assert count == 0
    zero, zero_count = step_batch(item, 0.4, states, 0.0, shocks)
    assert np.array_equal(zero, states)
    assert zero_count == 0
    assert np.array_equal(states, np.tile(np.asarray(state), (3, 1)))


@pytest.mark.parametrize(
    "kind,anti",
    [(SequenceKind.PSEUDO, False), (SequenceKind.PSEUDO, True), (SequenceKind.SOBOL, False)],
)
def test_full_paths_replay_across_batch_sizes(kind, anti):
    config = request(paths=256, batch=64, kind=kind, antithetic=anti)
    actual = paths(config)
    for size in (2, 8, 128, 1024):
        assert np.array_equal(actual, paths(replace(config, batch_size=size)))
    assert actual.shape == (256, 3, 1)
    assert np.all(actual[:, 0, 0] == 100)
    changed = replace(config, sequence=replace(config.sequence, key=StreamKey(20251002)))
    assert not np.array_equal(actual, paths(changed))


def test_partial_pseudo_batches_and_nonzero_grid_origin():
    config = replace(request(paths=13, batch=5), grid=TimeGrid((0.4, 0.5, 1.0)))
    batches = list(MonteCarloEngine().iter_batches(config))
    assert [(batch.start_path, batch.path_count) for batch in batches] == [(0, 5), (5, 5), (10, 3)]
    assert np.array_equal(paths(config), paths(replace(config, batch_size=13)))


def test_known_normal_and_gbm_terminal_distribution():
    normals = NormalStream(SequenceSpec(StreamKey(884)), 1, 100000).draw(100000)[:, 0]
    assert abs(np.mean(normals)) < 6 / math.sqrt(normals.size)
    assert abs(np.var(normals, ddof=1) - 1) < 6 * math.sqrt(2 / (normals.size - 1))
    assert kstest(normals, "norm").pvalue > 1e-4
    config = replace(request(paths=100000, batch=4096), grid=TimeGrid((0.0, 1.0)))
    terminal = paths(config)[:, -1, 0]
    model = config.components[0].process
    mean, variance = gbm_terminal_moments(model, 100.0, 1.0)
    assert abs(np.mean(terminal) - mean) < 6 * math.sqrt(variance / terminal.size)
    assert np.var(terminal, ddof=1) == pytest.approx(variance, rel=0.025)
    standardized = (np.log(terminal / 100) - (0.05 - 0.5 * 0.2**2)) / 0.2
    assert kstest(standardized, "norm").pvalue > 1e-4


@pytest.mark.parametrize(
    "model,initial",
    [
        (Vasicek(0.4, 0.05, 0.02), -0.01),
        (HullWhite(0.4, 0.02, LinearForwardCurve(0.03, 0.002)), 0.03),
    ],
)
def test_gaussian_rate_terminal_moments_on_irregular_grid(model, initial):
    item = component(model, state=(initial,), name="rate")
    config = replace(
        request(paths=100000, batch=4096), components=(item,), grid=TimeGrid((0.0, 0.1, 0.4, 1.7))
    )
    terminal = paths(config)[:, -1, 0]
    mean, variance = (
        model.moments(initial, 1.7)
        if isinstance(model, Vasicek)
        else model.moments(0.0, initial, 1.7)
    )
    assert abs(np.mean(terminal) - mean) < 6 * math.sqrt(variance / terminal.size)
    assert np.var(terminal, ddof=1) == pytest.approx(variance, rel=0.025)


def test_exact_ou_cross_covariance_uses_integrated_kernels():
    first = component(Vasicek(0.2, 0.03, 0.02), state=(0.02,), name="rate1")
    second = component(Vasicek(3.0, 0.04, 0.03), state=(0.03,), name="rate2")
    correlation = CorrelationMatrix(
        first.factor_names + second.factor_names, ((1.0, 0.7), (0.7, 1.0))
    )
    config = replace(
        request(paths=100000, batch=4096),
        components=(first, second),
        correlation=correlation,
        grid=TimeGrid((0.0, 1.0)),
    )
    expected_cov = (
        0.7
        * 0.02
        * 0.03
        * quad(lambda s: math.exp(-0.2 * (1 - s)) * math.exp(-3 * (1 - s)), 0, 1)[0]
    )
    actual = paths(config)[:, -1, :]
    assert np.cov(actual.T)[0, 1] == pytest.approx(expected_cov, rel=0.035)
    weighted = innovation_correlation(config, 1.0).values[0][1]
    assert weighted < 0.7
    assert weighted == pytest.approx(
        expected_cov
        / math.sqrt(first.process.moments(0.02, 1)[1] * second.process.moments(0.03, 1)[1]),
        rel=1e-13,
    )
    assert np.array_equal(actual, paths(replace(config, batch_size=20000))[:, -1, :])


def test_multistep_ou_and_gbm_dependence_reproduces_brownian_correlation():
    first = component(Vasicek(2.0, 0.03, 0.02), state=(0.02,), name="rate")
    second = component(name="asset")
    correlation = CorrelationMatrix(
        first.factor_names + second.factor_names, ((1.0, -0.6), (-0.6, 1.0))
    )
    config = replace(
        request(paths=100000, batch=4096), components=(first, second), correlation=correlation
    )
    actual = paths(config)[:, -1, :]
    expected = -0.6 * ou_loading(2.0, 1.0) / math.sqrt(ou_loading(4.0, 1.0))
    assert np.corrcoef(actual[:, 0], np.log(actual[:, 1]))[0, 1] == pytest.approx(
        expected, abs=0.012
    )
    # The target driver rho and exact-transition innovation correlation differ.
    assert abs(expected + 0.6) > 0.04


def test_multifactor_gbm_and_heston_loading_is_applied_once():
    item = component(
        Heston(1.5, 0.04, 0.3, -0.6, 0.03),
        state=(100.0, 0.04),
        name="heston",
        scheme=Scheme.HESTON_PROJECTED,
    )
    asset = component(name="other")
    correlation = CorrelationMatrix(
        item.factor_names + asset.factor_names, ((1.0, 0.0, 0.3), (0.0, 1.0, 0.2), (0.3, 0.2, 1.0))
    )
    config = replace(
        request(paths=100000, batch=4096),
        components=(item, asset),
        correlation=correlation,
        grid=TimeGrid((0.0, 0.0001)),
    )
    terminal = paths(config)[:, -1, :]
    measured = np.corrcoef(
        np.asarray([np.log(terminal[:, 0]), terminal[:, 1], np.log(terminal[:, 2])])
    )
    assert measured[0, 1] == pytest.approx(-0.6, abs=0.012)
    assert measured[0, 2] == pytest.approx(0.3, abs=0.012)
    assert measured[1, 2] == pytest.approx(-0.6 * 0.3 + 0.8 * 0.2, abs=0.012)


def test_projected_heston_counts_every_projection_without_hiding_bias():
    model = Heston(0.1, 0.0, 4.0, 0.0, 0.03)
    item = component(model, state=(100.0, 0.01), scheme=Scheme.HESTON_PROJECTED)
    states = np.asarray([[100.0, 0.01], [100.0, 0.01]])
    shocks = np.asarray([[0.0, -1.0], [0.0, 1.0]])
    output, projected = step_batch(item, 0.0, states, 1.0, shocks)
    assert projected == 1 and output[0, 1] == 0 and output[1, 1] > 0
    assert np.array_equal(states, np.asarray([[100.0, 0.01], [100.0, 0.01]]))
    with pytest.raises(ModelError):
        step_batch(replace(item, scheme=Scheme.EULER), 0.0, states, 1.0, shocks)
    config = replace(request(paths=64, batch=16), components=(item,), grid=TimeGrid((0.0, 1.0)))
    assert (
        sum(batch.variance_projection_count for batch in MonteCarloEngine().iter_batches(config))
        > 0
    )


@pytest.mark.parametrize(
    "states,shocks",
    [
        (np.asarray([[0.0]]), np.asarray([[0.0]])),
        (np.asarray([[100.0, 1.0]]), np.asarray([[0.0]])),
        (np.asarray([[100.0]]), np.asarray([[0.0, 0.0]])),
        (np.asarray([[100.0]]), np.asarray([[np.inf]])),
    ],
)
def test_kernel_rejects_invalid_input_even_at_zero_time(states, shocks):
    with pytest.raises((ModelError, SimulationError)):
        step_batch(component(), 0.0, states, 0.0, shocks)


def test_kernel_overflow_and_euler_negative_spot_are_explicit():
    with pytest.raises(NumericalError):
        step_batch(component(), 0, np.asarray([[100.0]]), 1, np.asarray([[10000.0]]))
    with pytest.raises(ModelError):
        step_batch(
            component(scheme=Scheme.EULER), 0, np.asarray([[100.0]]), 1, np.asarray([[-100.0]])
        )
    item = component(Heston(1.0, 0.04, 0.3, 0.0, 0.02), state=(100.0, 0.04), scheme=Scheme.EULER)
    with pytest.raises(ModelError):
        step_batch(item, 0, np.asarray([[100.0, -1.0]]), 0, np.asarray([[0.0, 0.0]]))


def test_gbm_analytical_references_include_deterministic_and_numeric_boundaries():
    model = GeometricBrownianMotion(0.0, 0.0)
    assert gbm_terminal_moments(model, 100, 1) == (100, 0)
    assert gbm_call_expectation(model, 100, 1, 90) == 10
    model = GeometricBrownianMotion(0.05, 0.2)
    assert math.exp(-0.05) * gbm_call_expectation(model, 100, 1, 100) == pytest.approx(
        10.450583572185565, abs=1e-12
    )
    with pytest.raises(NumericalError):
        gbm_terminal_moments(GeometricBrownianMotion(0.0, 100.0), 100, 1)
