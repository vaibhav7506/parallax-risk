"""Model domains, finite arithmetic, unsupported schemes and quadrature failures."""

import math
from dataclasses import FrozenInstanceError

import pytest

from parallax_risk.common.errors import ModelError, NumericalError, ParallaxError
from parallax_risk.domain.models.assets import GeometricBrownianMotion as GBM
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.base import checked_exp, ou_loading, positive, vector
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


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Vasicek(0, 0.02, 0.01),
        lambda: Vasicek(-1, 0.02, 0.01),
        lambda: Vasicek(0.1, float("nan"), 0.01),
        lambda: Vasicek(0.1, 0.02, -0.01),
        lambda: HullWhite(0.1, -0.01, LinearForwardCurve(0.03)),
        lambda: HullWhite(0.1, 0.01, object()),
        lambda: GBM(float("inf"), 0.2),
        lambda: GBM(0.03, -0.1),
        lambda: Heston(0, 0.04, 0.3, -0.7, 0.03),
        lambda: Heston(1, -0.04, 0.3, -0.7, 0.03),
        lambda: Heston(1, 0.04, -0.3, -0.7, 0.03),
        lambda: Heston(1, 0.04, 0.3, -1.01, 0.03),
        lambda: Heston(1, 0.04, 0.3, 1.01, 0.03),
        lambda: Heston(1, 0.04, 0.3, False, 0.03),
        lambda: LinearForwardCurve(float("nan")),
        lambda: LinearForwardCurve(0.02, float("inf")),
    ],
)
def test_invalid_parameters_rejected(factory):
    with pytest.raises(ParallaxError):
        factory()


@pytest.mark.parametrize(
    "model,state",
    [
        (Vasicek(0.1, 0.02, 0.01), (float("nan"),)),
        (Vasicek(0.1, 0.02, 0.01), (0.02, 0.03)),
        (Vasicek(0.1, 0.02, 0.01), [0.02]),
        (GBM(0.03, 0.2), (0.0,)),
        (GBM(0.03, 0.2), (-1.0,)),
        (Heston(1, 0.04, 0.3, -0.7, 0.03), (100.0, -0.01)),
        (Heston(1, 0.04, 0.3, -0.7, 0.03), (0.0, 0.04)),
    ],
)
def test_invalid_states_rejected(model, state):
    with pytest.raises(ParallaxError):
        model.validate_state(state)


@pytest.mark.parametrize(
    "model,state,shocks",
    [
        (Vasicek(0.3, 0.04, 0.01), (-0.02,), (0.0,)),
        (HullWhite(0.2, 0.01, LinearForwardCurve(0.03)), (-0.02,), (0.0,)),
        (GBM(0.03, 0.2), (100.0,), (0.0,)),
        (Heston(1, 0.04, 0.3, -0.7, 0.03), (100.0, 0.04), (0.0, 0.0)),
    ],
)
def test_zero_step_identity_and_coefficients(model, state, shocks):
    assert EulerMaruyama().step(model, 0, state, 0, shocks) == state
    assert len(model.drift(0, state)) == model.state_dimension
    assert len(model.diffusion(0, state)) == model.state_dimension
    if not isinstance(model, Heston):
        assert ExactTransition().step(model, 0, state, 0, shocks) == state
    else:
        assert HestonProjectedEuler().step(model, 0, state, 0, shocks) == state


@pytest.mark.parametrize(
    "time,dt,shocks",
    [
        (-1, 1, (0.0,)),
        (0, -1, (0.0,)),
        (0, 0, (float("nan"),)),
        (0, 0, ()),
        (0, 1, [0.0]),
        (1e308, 1e308, (0.0,)),
    ],
)
def test_invalid_steps_rejected_even_at_zero(time, dt, shocks):
    with pytest.raises(ParallaxError):
        ExactTransition().step(Vasicek(0.1, 0.03, 0.01), time, (0.02,), dt, shocks)


def test_schemes_do_not_silently_clip_or_fallback():
    heston = Heston(1, 0.04, 0.3, -0.7, 0.03)
    with pytest.raises(ModelError, match="analytical"):
        ExactTransition().step(heston, 0, (100.0, 0.04), 0.1, (0.0, 0.0))
    with pytest.raises(ModelError, match="requires a Heston"):
        HestonProjectedEuler().step(GBM(0.03, 0.2), 0, (100.0,), 0.1, (0.0,))
    with pytest.raises(ModelError, match="spot"):
        EulerMaruyama().step(GBM(0.03, 0.2), 0, (100.0,), 1, (-10.0,))
    with pytest.raises(ModelError, match="variance"):
        EulerMaruyama().step(heston, 0, (100.0, 0.04), 1, (0.0, -10.0))


def test_custom_process_diffusion_shape_is_checked():
    class BadProcess:
        state_dimension = 1
        driver_dimension = 1

        def validate_state(self, state):
            return vector(state, 1, "state")

        def drift(self, time, state):
            return (0.0,)

        def diffusion(self, time, state):
            return ()

    with pytest.raises(ModelError, match="row count"):
        EulerMaruyama().step(BadProcess(), 0, (1.0,), 0.1, (0.0,))


@pytest.mark.parametrize(
    "function",
    [
        lambda: checked_exp(1000),
        lambda: checked_exp(-1000),
        lambda: positive(0, "zero"),
        lambda: ou_loading(1e308, 10),
        lambda: Vasicek(0.1, 0.02, 1e200).moments(0.02, 1),
        lambda: GBM(0.01, 1e200).exact_transition(0, (100.0,), 1, (0.0,)),
        lambda: LinearForwardCurve(1e308).discount(10),
        lambda: LinearForwardCurve(1e308, 1e308).forward(10),
    ],
)
def test_range_errors_are_explicit(function):
    with pytest.raises(ParallaxError):
        function()


def test_maturity_order_and_immutability():
    curve = LinearForwardCurve(0.03)
    hw = HullWhite(0.2, 0.01, curve)
    with pytest.raises(ModelError):
        hw.bond(2, 1, 0.03)
    with pytest.raises(ModelError):
        hw.bond_call(2, 1, 1.0)
    with pytest.raises(FrozenInstanceError):
        hw.speed = 0.3
    assert hw.bond_call(0, 1, 1) == max(curve.discount(1) - 1, 0)


@pytest.mark.parametrize(
    "args", [(0, 1e-9, 250), (1e-7, 0, 250), (1e-7, 1, 250), (1e-7, 1e-9, 1), (1e-7, 1e-9, True)]
)
def test_invalid_fourier_settings(args):
    with pytest.raises(ParallaxError):
        FourierSettings(*args)


def test_quadrature_nonconvergence_and_invalid_inputs_rejected():
    model = Heston(2, 0.04, 0.3, -0.7, 0.05)
    with pytest.raises(NumericalError, match="convergence"):
        heston_call(model, 100, 0.04, 100, 1, FourierSettings(1e-12, 1e-12, 2))
    with pytest.raises(NumericalError, match="FourierSettings"):
        heston_call(model, 100, 0.04, 100, 1, object())
    with pytest.raises(ParallaxError):
        heston_call(model, 100, 0.04, -100, 1)
    with pytest.raises(ParallaxError):
        heston_call(model, 100, 0.04, 100, -1)
    with pytest.raises(NumericalError):
        characteristic_function(model, 100, 0.04, 1, complex(math.inf, 0))
    assert characteristic_function(model, 100, 0.04, 0, 1) == pytest.approx(
        complex(math.cos(math.log(100)), math.sin(math.log(100))), abs=1e-15
    )
