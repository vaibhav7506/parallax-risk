"""Shared finite-state process and one-step discretization contracts."""

import math
from typing import Protocol, runtime_checkable

from parallax_risk.common.errors import ModelError, NumericalError
from parallax_risk.common.math import require_finite

type State = tuple[float, ...]
type Matrix = tuple[tuple[float, ...], ...]


def nonnegative(value: float, name: str) -> float:
    """Require a finite nonnegative parameter, including exact zero boundaries."""
    result = require_finite(value, name=name)
    if result < 0:
        raise ModelError(f"{name} must be nonnegative")
    return result


def positive(value: float, name: str) -> float:
    """Require a finite strictly positive parameter."""
    result = nonnegative(value, name)
    if result == 0:
        raise ModelError(f"{name} must be positive")
    return result


def vector(values: State, size: int, name: str) -> State:
    """Finite immutable vector with explicit dimensionality; no coercion from lists."""
    if not isinstance(values, tuple) or len(values) != size:
        raise ModelError(f"{name} must be an immutable tuple of length {size}")
    return tuple(require_finite(value, name=name) for value in values)


def checked_exp(value: float) -> float:
    """Finite, strictly positive exponential; underflow is an explicit numerical error."""
    try:
        return positive(math.exp(require_finite(value, name="exponent")), "exponential")
    except OverflowError:
        raise NumericalError("Model exponential overflowed") from None


def ou_loading(speed: float, time: float) -> float:
    """(1-exp(-a*t))/a, stable near a*t=0 with strictly positive a."""
    speed = positive(speed, "OU speed")
    time = nonnegative(time, "OU time")
    exponent = require_finite(speed * time, name="OU exponent")
    return nonnegative(-math.expm1(-exponent) / speed, "OU loading")


def square(value: float) -> float:
    """Checked binary64 square, preventing raw power overflow and silent infinity."""
    value = require_finite(value, name="square argument")
    return nonnegative(value * value, "squared value")


@runtime_checkable
class StochasticProcess(Protocol):
    """State drift and diffusion against independent standardized Brownian factors.

    Time is year fractions. Diffusion rows are state components, columns are
    independent drivers. Correlation is encoded in the loading, never applied twice.
    """

    @property
    def state_dimension(self) -> int: ...

    @property
    def driver_dimension(self) -> int: ...

    def validate_state(self, state: State) -> State: ...

    def drift(self, time: float, state: State) -> State: ...

    def diffusion(self, time: float, state: State) -> Matrix: ...


@runtime_checkable
class ExactProcess(StochasticProcess, Protocol):
    """Closed-form marginal transition; not a joint transition for integrated rates."""

    def exact_transition(self, time: float, state: State, dt: float, shocks: State) -> State: ...


class Discretization(Protocol):
    """A single step supplied with independent standard-normal shocks by its caller."""

    def step(
        self, process: StochasticProcess, time: float, state: State, dt: float, shocks: State
    ) -> State: ...


def step_inputs(
    process: StochasticProcess, time: float, state: State, dt: float, shocks: State
) -> tuple[float, State, float, State]:
    """Shared validation, also at dt=0; no invalid input is ignored at a boundary."""
    time = nonnegative(time, "time")
    dt = nonnegative(dt, "time step")
    require_finite(time + dt, name="end time")
    return (
        time,
        process.validate_state(state),
        dt,
        vector(shocks, process.driver_dimension, "shocks"),
    )
