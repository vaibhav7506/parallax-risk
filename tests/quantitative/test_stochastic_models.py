"""Analytical, independent quadrature/ODE and supplied-shock discretization checks."""

import math

import numpy as np
import pytest
from scipy.integrate import quad, solve_ivp

from parallax_risk.domain.models.assets import GeometricBrownianMotion, Heston
from parallax_risk.domain.models.discretization import (
    EulerMaruyama,
    ExactTransition,
    HestonProjectedEuler,
)
from parallax_risk.domain.models.heston_pricing import (
    FourierSettings,
    characteristic_function,
    heston_call,
)
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve, Vasicek


@pytest.mark.parametrize("speed", [1e-9, 1e-4, 0.1, 1.5])
def test_vasicek_bond_against_independent_gaussian_integral(speed):
    rate, level, sigma, tau = -0.01, 0.04, 0.015, 3.0
    # Integrating deterministic mean and squared kernel avoids affine A/B algebra.
    mean = quad(lambda s: level + (rate - level) * math.exp(-speed * s), 0, tau, epsabs=1e-13)[0]
    variance = (
        sigma
        * sigma
        * quad(lambda s: (-math.expm1(-speed * s) / speed) ** 2, 0, tau, epsabs=1e-13)[0]
    )
    assert Vasicek(speed, level, sigma).bond(rate, tau) == pytest.approx(
        math.exp(-mean + 0.5 * variance), abs=3e-13, rel=0
    )


def test_gaussian_moments_and_exact_shock_loading():
    model = Vasicek(0.4, 0.05, 0.02)
    mean, variance = model.moments(0.01, 2.0)
    assert mean == pytest.approx(0.05 + (0.01 - 0.05) * math.exp(-0.8), abs=1e-15)
    assert variance == pytest.approx(0.02**2 * (1 - math.exp(-1.6)) / 0.8, abs=1e-16)
    value = ExactTransition().step(model, 1.0, (0.01,), 2.0, (1.25,))[0]
    assert value == pytest.approx(mean + math.sqrt(variance) * 1.25, abs=1e-15)
    assert model.bond(0.02, 0.0) == 1.0


@pytest.mark.parametrize("time", [0.0, 0.5, 3.0, 15.0])
def test_hull_white_fits_initial_curve_and_shift_derivative(time):
    curve = LinearForwardCurve(0.03, -0.0001)
    model = HullWhite(0.2, 0.012, curve)
    assert model.bond(0.0, time, curve.level) == pytest.approx(curve.discount(time), abs=1e-15)
    dt = 1e-5
    derivative = (model.shift(time + dt) - model.shift(max(0, time - dt))) / (
        dt if time == 0 else 2 * dt
    )
    assert model.drift(time, (model.shift(time),))[0] == pytest.approx(derivative, abs=1e-9)
    assert model.bond(time, time, 0.03) == 1.0


def test_hull_white_exact_mean_and_conditional_bond_identity():
    curve = LinearForwardCurve(0.025, 0.001)
    model = HullWhite(0.15, 0.018, curve)
    time, dt, rate = 2.0, 0.7, -0.005
    mean, variance = model.moments(time, rate, dt)
    assert mean == pytest.approx(
        (rate - model.shift(time)) * math.exp(-0.15 * dt) + model.shift(time + dt), abs=1e-15
    )
    assert variance == pytest.approx(0.018**2 * (1 - math.exp(-0.3 * dt)) / 0.3, abs=1e-16)
    # Independent conditional integrated-Gaussian bond pricing.
    maturity = 6.0
    mean_integral = quad(lambda s: model.moments(time, rate, s - time)[0], time, maturity)[0]
    variance_integral = (
        0.018**2
        * quad(lambda s: ((1 - math.exp(-0.15 * (maturity - s))) / 0.15) ** 2, time, maturity)[0]
    )
    assert model.bond(time, maturity, rate) == pytest.approx(
        math.exp(-mean_integral + 0.5 * variance_integral), abs=1e-13
    )


def test_hull_white_bond_option_against_forward_gaussian_quadrature():
    curve = LinearForwardCurve(0.03, 0.001)
    model = HullWhite(0.18, 0.012, curve)
    expiry, maturity, strike = 2.0, 7.0, 0.86
    forward = curve.discount(maturity) / curve.discount(expiry)
    sigma = (
        0.012
        * (1 - math.exp(-0.18 * (maturity - expiry)))
        / 0.18
        * math.sqrt((1 - math.exp(-0.36 * expiry)) / 0.36)
    )
    threshold = (math.log(strike / forward) + sigma * sigma / 2) / sigma
    price = (
        curve.discount(expiry)
        * quad(
            lambda z: (
                (forward * math.exp(-sigma * sigma / 2 + sigma * z) - strike)
                * math.exp(-z * z / 2)
                / math.sqrt(2 * math.pi)
            ),
            threshold,
            12,
            epsabs=1e-13,
        )[0]
    )
    assert model.bond_call(expiry, maturity, strike) == pytest.approx(price, abs=2e-13)
    assert HullWhite(0.18, 0.0, curve).bond_call(expiry, maturity, strike) == max(
        curve.discount(maturity) - strike * curve.discount(expiry), 0
    )


@pytest.mark.parametrize(
    "model,state",
    [
        (Vasicek(0.4, 0.03, 0.02), (0.01,)),
        (HullWhite(0.2, 0.01, LinearForwardCurve(0.03, 0.001)), (0.02,)),
        (GeometricBrownianMotion(0.03, 0.2), (100.0,)),
    ],
)
def test_euler_local_refinement_against_exact_single_step(model, state):
    # Same supplied standardized shock; local agreement, not a path strong-order claim.
    differences = []
    for dt in (1e-2, 1e-3, 1e-4):
        exact = ExactTransition().step(model, 0.5, state, dt, (0.4,))[0]
        approximate = EulerMaruyama().step(model, 0.5, state, dt, (0.4,))[0]
        differences.append(abs(exact - approximate))
    assert differences[2] < differences[1] < differences[0]
    assert differences[2] < 5e-4


def test_gbm_exact_transition_and_heston_independent_driver_covariance():
    gbm = GeometricBrownianMotion(0.05, 0.2)
    assert gbm.exact_transition(0, (100.0,), 0.5, (-0.7,))[0] == pytest.approx(
        100 * math.exp((0.05 - 0.5 * 0.2**2) * 0.5 + 0.2 * math.sqrt(0.5) * (-0.7)), abs=1e-13
    )
    heston = Heston(2, 0.04, 0.3, -0.7, 0.03, 0.01)
    loading = np.asarray(heston.diffusion(0, (100.0, 0.04)))
    covariance = loading @ loading.T
    assert covariance[0, 0] == pytest.approx(100**2 * 0.04, abs=1e-12)
    assert covariance[1, 1] == pytest.approx(0.3**2 * 0.04, abs=1e-16)
    assert covariance[0, 1] == pytest.approx(100 * 0.3 * 0.04 * (-0.7), abs=1e-15)
    diagnostic = HestonProjectedEuler().step_with_diagnostics(
        heston, 0, (100.0, 0.04), 1.0, (0.0, -10.0)
    )
    assert diagnostic.variance_projected and diagnostic.variance_proposal < 0
    assert diagnostic.state[1] == 0 and diagnostic.state[0] > 0
    assert HestonProjectedEuler().step(heston, 0, (100.0, 0.0), 0.1, (0.0, 0.0))[
        1
    ] == pytest.approx(0.008, abs=1e-15)


@pytest.mark.parametrize("u", [0.2, 2.0, 8.0, complex(2, -0.5)])
@pytest.mark.parametrize("expiry", [1e-8, 2.0])
def test_heston_characteristic_function_against_independent_riccati_ode(u, expiry):
    model = Heston(1.5, 0.045, 0.35, -0.65, 0.03, 0.01)
    spot, v0 = 100.0, 0.035
    iu = 1j * u

    def rhs(t, y):
        c, d = y
        return [
            model.speed * model.variance_level * d,
            0.5 * model.vol_of_variance**2 * d * d
            + (model.correlation * model.vol_of_variance * iu - model.speed) * d
            - 0.5 * (u * u + iu),
        ]

    solution = solve_ivp(rhs, (0, expiry), np.array([0j, 0j]), rtol=1e-11, atol=1e-13)
    assert solution.success
    c, d = solution.y[:, -1]
    expected = np.exp(iu * (math.log(spot) + (0.03 - 0.01) * expiry) + c + d * v0)
    assert characteristic_function(model, spot, v0, expiry, u) == pytest.approx(expected, abs=1e-10)


def test_heston_fourier_tolerance_stability_and_price_benchmark():
    model = Heston(2, 0.04, 0.3, -0.7, 0.05)
    price = heston_call(model, 100, 0.04, 100, 1)
    assert price.value == pytest.approx(10.394218565150, abs=5e-9)
    assert price.estimated_absolute_error <= 1e-7 and price.integrand_evaluations > 0
    tighter = heston_call(model, 100, 0.04, 100, 1, FourierSettings(1e-9, 1e-12, 500))
    assert tighter.value == pytest.approx(price.value, abs=2e-8)
    assert price.method == "lewis_infinite_quadrature"


def test_heston_gaussian_and_absorbing_boundaries():
    gaussian = Heston(2, 0.04, 0, -0.7, 0.05)
    price = heston_call(gaussian, 100, 0.04, 100, 1)
    assert price.value == pytest.approx(10.450583572185565, abs=1e-12)
    assert price.method == "deterministic_variance"
    assert characteristic_function(gaussian, 100, 0.04, 1, 0) == 1
    assert heston_call(gaussian, 100, 0.04, 90, 0).value == 10
    absorbing = Heston(2, 0, 0.3, 1, 0.05)
    assert heston_call(absorbing, 100, 0, 100, 1).value == pytest.approx(
        100 - 100 * math.exp(-0.05), abs=1e-13
    )
    assert heston_call(Heston(2, 0.04, 0, 1, 0.05), 100, 0, 100, 1).value > 0


@pytest.mark.parametrize("rho", [-1.0, 1.0])
def test_heston_correlation_boundaries_and_non_feller_parameters(rho):
    model = Heston(0.8, 0.04, 0.5, rho, 0.03)
    assert model.feller_margin < 0
    result = heston_call(model, 100, 0.04, 100, 1)
    assert 0 < result.value < 100
    assert model.diffusion(0, (100, 0.04))[1][1] == 0


@pytest.mark.parametrize("xi", [1e-4, 1e-7, 1e-10])
def test_fourier_pricing_approaches_gaussian_without_small_xi_fallback(xi):
    result = heston_call(Heston(2, 0.04, xi, 0, 0.05), 100, 0.04, 100, 1)
    assert result.method == "lewis_infinite_quadrature"
    assert result.value == pytest.approx(10.450583572185565, abs=2e-6)
