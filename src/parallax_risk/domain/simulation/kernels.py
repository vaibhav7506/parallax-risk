"""Vectorized binary64 kernels reconciled against the Phase 3 scalar strategies."""

import math

import numpy as np

from parallax_risk.common.errors import ModelError, NumericalError
from parallax_risk.domain.models.assets import GeometricBrownianMotion, Heston
from parallax_risk.domain.models.base import nonnegative, ou_loading, square
from parallax_risk.domain.models.rates import HullWhite, Vasicek
from parallax_risk.domain.simulation.arrays import FloatArray, finite_array
from parallax_risk.domain.simulation.contracts import ProcessComponent, Scheme


def _state(component: ProcessComponent, state: FloatArray) -> None:
    finite_array(state, ndim=2, name="batch state")
    if state.shape[1] != component.process.state_dimension:
        raise ModelError("Batch state has the wrong component dimension")
    if isinstance(component.process, (GeometricBrownianMotion, Heston)):
        if np.any(state[:, 0] <= 0):
            raise ModelError("Every simulated spot must be strictly positive")
        if isinstance(component.process, Heston) and np.any(state[:, 1] < 0):
            raise ModelError("Every simulated variance must be nonnegative")


def step_batch(
    component: ProcessComponent, time: float, state: FloatArray, dt: float, shocks: FloatArray
) -> tuple[FloatArray, int]:
    """Allocate a new working state; never mutate caller inputs. Only paths are published.

    Projected-variance counts are model steps (paths x times), not distinct paths.
    Numeric overflow/invalid operations fail; only the selected Heston scheme projects.
    """
    _state(component, state)
    finite_array(shocks, ndim=2, name="batch shocks")
    if shocks.shape != (state.shape[0], component.process.driver_dimension):
        raise ModelError("Batch shocks do not match path and driver dimensions")
    time = nonnegative(time, "step time")
    dt = nonnegative(dt, "step length")
    nonnegative(time + dt, "end time")
    if dt == 0:
        return state.copy(), 0
    model = component.process
    projections = 0
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            root_dt = math.sqrt(dt)
            if isinstance(model, GeometricBrownianMotion):
                if component.scheme == Scheme.EXACT:
                    exponent = (model.drift_rate - 0.5 * square(model.volatility)) * dt
                    next_state = state * np.exp(exponent + model.volatility * root_dt * shocks)
                else:
                    next_state = (
                        state
                        + model.drift_rate * state * dt
                        + model.volatility * state * root_dt * shocks
                    )
            elif isinstance(model, (Vasicek, HullWhite)):
                if component.scheme == Scheme.EXACT:
                    conditional_variance = square(model.volatility) * ou_loading(
                        2 * model.speed, dt
                    )
                    decay = math.exp(-model.speed * dt)
                    if isinstance(model, Vasicek):
                        mean = model.level + (state - model.level) * decay
                    else:
                        mean = (state - model.shift(time)) * decay + model.shift(time + dt)
                    next_state = mean + math.sqrt(conditional_variance) * shocks
                else:
                    if isinstance(model, Vasicek):
                        drift = model.speed * (model.level - state)
                    else:
                        drift = model.speed * (model.initial_curve.forward(time) - state)
                        drift += model.initial_curve.slope + square(model.volatility) * ou_loading(
                            2 * model.speed, time
                        )
                    next_state = state + drift * dt + model.volatility * root_dt * shocks
            else:
                spot, variance = state[:, 0], state[:, 1]
                root = np.sqrt(variance * dt)
                zv = (
                    model.correlation * shocks[:, 0]
                    + math.sqrt(1 - model.correlation**2) * shocks[:, 1]
                )
                proposal = (
                    variance
                    + model.speed * (model.variance_level - variance) * dt
                    + model.vol_of_variance * root * zv
                )
                if component.scheme == Scheme.HESTON_PROJECTED:
                    spot_next = spot * np.exp(
                        (model.rate - model.dividend - 0.5 * variance) * dt + root * shocks[:, 0]
                    )
                    projections = int(np.count_nonzero(proposal < 0))
                    variance_next = np.maximum(proposal, 0.0)
                else:
                    spot_next = (
                        spot
                        + (model.rate - model.dividend) * spot * dt
                        + spot * root * shocks[:, 0]
                    )
                    variance_next = proposal
                next_state = np.column_stack((spot_next, variance_next))
    except (FloatingPointError, OverflowError) as error:
        raise NumericalError("Vectorized model arithmetic overflowed or became invalid") from error
    _state(component, next_state)
    return next_state, projections
