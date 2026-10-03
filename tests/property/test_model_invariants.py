"""Finite scalar properties; randomness in tests is not a production path engine."""

import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve, Vasicek


@given(
    st.floats(0.001, 2, allow_nan=False),
    st.floats(0, 0.1, allow_nan=False),
    st.floats(-0.1, 0.1, allow_nan=False),
    st.floats(0, 20, allow_nan=False),
)
def test_gaussian_curve_fit_and_positive_discount(speed, sigma, rate, time):
    curve = LinearForwardCurve(rate)
    hw = HullWhite(speed, sigma, curve)
    assert math.isclose(hw.bond(0, time, rate), curve.discount(time), rel_tol=1e-12, abs_tol=1e-14)
    assert Vasicek(speed, rate, sigma).bond(rate, time) > 0


@given(st.floats(-0.95, 0.95, allow_nan=False))
def test_two_factor_cholesky_reconstructs_declared_correlation(rho):
    matrix = CorrelationMatrix(("a", "b"), ((1.0, rho), (rho, 1.0)))
    factor = np.asarray(matrix.cholesky())
    assert np.max(np.abs(factor @ factor.T - np.asarray(matrix.values))) < 1e-14


@given(st.floats(1e-3, 1e4, allow_nan=False), st.floats(-5, 5, allow_nan=False))
def test_gbm_exact_transition_remains_positive(spot, shock):
    assert GeometricBrownianMotion(0.03, 0.2).exact_transition(0, (spot,), 1, (shock,))[0] > 0
