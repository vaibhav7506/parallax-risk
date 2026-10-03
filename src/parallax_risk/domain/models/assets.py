"""GBM and Heston coefficients with independent-driver diffusion loadings."""

import math
from dataclasses import dataclass

from parallax_risk.common.errors import ModelError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.base import (
    Matrix,
    State,
    checked_exp,
    nonnegative,
    positive,
    square,
    step_inputs,
    vector,
)


@dataclass(frozen=True, slots=True)
class GeometricBrownianMotion:
    """dS=mu*S dt+sigma*S dW; caller specifies mu and measure, never inferred."""

    drift_rate: float
    volatility: float

    def __post_init__(self) -> None:
        require_finite(self.drift_rate, name="GBM drift rate")
        nonnegative(self.volatility, "GBM volatility")

    @property
    def state_dimension(self) -> int:
        return 1

    @property
    def driver_dimension(self) -> int:
        return 1

    def validate_state(self, state: State) -> State:
        state = vector(state, 1, "GBM spot state")
        positive(state[0], "spot")
        return state

    def drift(self, time: float, state: State) -> State:
        nonnegative(time, "time")
        state = self.validate_state(state)
        return (require_finite(self.drift_rate * state[0], name="GBM drift"),)

    def diffusion(self, time: float, state: State) -> Matrix:
        nonnegative(time, "time")
        state = self.validate_state(state)
        return ((require_finite(self.volatility * state[0], name="GBM diffusion"),),)

    def exact_transition(self, time: float, state: State, dt: float, shocks: State) -> State:
        _, state, dt, shocks = step_inputs(self, time, state, dt, shocks)
        exponent = (
            self.drift_rate - 0.5 * square(self.volatility)
        ) * dt + self.volatility * math.sqrt(dt) * shocks[0]
        return self.validate_state((require_finite(state[0] * checked_exp(exponent), name="spot"),))


@dataclass(frozen=True, slots=True)
class Heston:
    """Q dynamics: dS=(r-q)Sdt+sqrt(v)S dW_s, dv=k(theta-v)dt+xi sqrt(v)dW_v.

    Supplied shocks are independent. rho is embedded in the second diffusion row.
    k>0, theta>=0, xi>=0, |rho|<=1. Feller is a diagnostic, not an input constraint.
    """

    speed: float
    variance_level: float
    vol_of_variance: float
    correlation: float
    rate: float
    dividend: float = 0.0

    def __post_init__(self) -> None:
        positive(self.speed, "variance mean reversion")
        nonnegative(self.variance_level, "long-run variance")
        nonnegative(self.vol_of_variance, "volatility of variance")
        rho = require_finite(self.correlation, name="Heston correlation")
        if not -1 <= rho <= 1:
            raise ModelError("Heston correlation must be in [-1,1]")
        require_finite(self.rate, name="risk-free rate")
        require_finite(self.dividend, name="continuous dividend yield")

    @property
    def state_dimension(self) -> int:
        return 2

    @property
    def driver_dimension(self) -> int:
        return 2

    @property
    def feller_margin(self) -> float:
        """2*k*theta-xi^2; positive margin and v0>0 imply inaccessible zero boundary."""
        return require_finite(
            2 * self.speed * self.variance_level - square(self.vol_of_variance),
            name="Feller margin",
        )

    def validate_state(self, state: State) -> State:
        state = vector(state, 2, "Heston spot/variance state")
        positive(state[0], "spot")
        nonnegative(state[1], "instantaneous variance")
        return state

    def drift(self, time: float, state: State) -> State:
        nonnegative(time, "time")
        spot, variance = self.validate_state(state)
        return vector(
            ((self.rate - self.dividend) * spot, self.speed * (self.variance_level - variance)),
            2,
            "Heston drift",
        )

    def diffusion(self, time: float, state: State) -> Matrix:
        nonnegative(time, "time")
        spot, variance = self.validate_state(state)
        root_v = math.sqrt(variance)
        variance_loading = require_finite(self.vol_of_variance * root_v, name="variance loading")
        return (
            (require_finite(spot * root_v, name="spot loading"), 0.0),
            (
                variance_loading * self.correlation,
                variance_loading * math.sqrt(1 - self.correlation**2),
            ),
        )
