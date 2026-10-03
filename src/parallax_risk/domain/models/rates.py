"""Risk-neutral Gaussian short-rate models and analytical default-free bonds."""

import math
from dataclasses import dataclass

from parallax_risk.common.errors import ModelError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.base import (
    Matrix,
    State,
    checked_exp,
    nonnegative,
    ou_loading,
    positive,
    square,
    step_inputs,
    vector,
)


@dataclass(frozen=True, slots=True)
class LinearForwardCurve:
    """Explicit smooth initial instantaneous forward f(0,t)=level+slope*t.

    Level: decimal/year; slope: decimal/year^2. Not inferred by differentiating
    the piecewise Phase 2 discount curve. Negative forwards are permitted.
    """

    level: float
    slope: float = 0.0

    def __post_init__(self) -> None:
        require_finite(self.level, name="forward level")
        require_finite(self.slope, name="forward slope")

    def forward(self, time: float) -> float:
        time = nonnegative(time, "time")
        return require_finite(self.level + self.slope * time, name="instantaneous forward")

    def discount(self, time: float) -> float:
        time = nonnegative(time, "time")
        return checked_exp(-self.level * time - 0.5 * self.slope * time * time)


@dataclass(frozen=True, slots=True)
class Vasicek:
    """dr=a(theta-r)dt+sigma*dW under Q; all times in years, rates decimal.

    a>0 (1/year), theta finite (1/year), sigma>=0 (rate/sqrt(year)).
    Negative rates are valid; no market-price-of-risk parameter is inferred.
    """

    speed: float
    level: float
    volatility: float

    def __post_init__(self) -> None:
        positive(self.speed, "mean reversion")
        require_finite(self.level, name="long-run rate")
        nonnegative(self.volatility, "rate volatility")

    @property
    def state_dimension(self) -> int:
        return 1

    @property
    def driver_dimension(self) -> int:
        return 1

    def validate_state(self, state: State) -> State:
        return vector(state, 1, "short-rate state")

    def drift(self, time: float, state: State) -> State:
        nonnegative(time, "time")
        (rate,) = self.validate_state(state)
        return (require_finite(self.speed * (self.level - rate), name="rate drift"),)

    def diffusion(self, time: float, state: State) -> Matrix:
        nonnegative(time, "time")
        self.validate_state(state)
        return ((self.volatility,),)

    def moments(self, rate: float, dt: float) -> tuple[float, float]:
        rate = require_finite(rate, name="rate")
        dt = nonnegative(dt, "time step")
        if dt == 0:
            return rate, 0.0
        mean = self.level + (rate - self.level) * math.exp(-self.speed * dt)
        variance = square(self.volatility) * ou_loading(2 * self.speed, dt)
        return require_finite(mean, name="conditional mean"), nonnegative(variance, "variance")

    def exact_transition(self, time: float, state: State, dt: float, shocks: State) -> State:
        _, state, dt, shocks = step_inputs(self, time, state, dt, shocks)
        mean, variance = self.moments(state[0], dt)
        return self.validate_state(
            (require_finite(mean + math.sqrt(variance) * shocks[0], name="rate"),)
        )

    def bond(self, rate: float, maturity: float) -> float:
        """P(t,t+tau) = E_Q[exp(-integral r ds)|r(t)]; unit nominal.

        Gaussian integral evaluated with a small-a*t series to avoid cancellation.
        Series error is O((a*t)^7) relative in the variance loading.
        """
        rate = require_finite(rate, name="rate")
        tau = nonnegative(maturity, "bond time to maturity")
        b = ou_loading(self.speed, tau)
        mean_integral = rate * b + self.level * (tau - b)
        x = self.speed * tau
        if x < 1e-3:
            variance_loading = (square(tau) * tau) * (
                1 / 3
                - x / 4
                + 7 * x * x / 60
                - x**3 / 24
                + 31 * x**4 / 2520
                - x**5 / 320
                + 127 * x**6 / 181440
            )
        else:
            variance_loading = (tau - 2 * b + ou_loading(2 * self.speed, tau)) / square(self.speed)
        variance_integral = nonnegative(
            square(self.volatility) * variance_loading, "integrated variance"
        )
        return checked_exp(-mean_integral + 0.5 * variance_integral)


@dataclass(frozen=True, slots=True)
class HullWhite:
    """One-factor Hull-White r=x+phi(t), dx=-a*x dt+sigma*dW under Q."""

    speed: float
    volatility: float
    initial_curve: LinearForwardCurve

    def __post_init__(self) -> None:
        positive(self.speed, "mean reversion")
        nonnegative(self.volatility, "rate volatility")
        if not isinstance(self.initial_curve, LinearForwardCurve):
            raise ModelError("Hull-White requires an explicit smooth LinearForwardCurve")

    @property
    def state_dimension(self) -> int:
        return 1

    @property
    def driver_dimension(self) -> int:
        return 1

    def validate_state(self, state: State) -> State:
        return vector(state, 1, "short-rate state")

    def shift(self, time: float) -> float:
        time = nonnegative(time, "time")
        return require_finite(
            self.initial_curve.forward(time)
            + 0.5 * square(self.volatility * ou_loading(self.speed, time)),
            name="Hull-White shift",
        )

    def drift(self, time: float, state: State) -> State:
        time = nonnegative(time, "time")
        (rate,) = self.validate_state(state)
        return (
            require_finite(
                self.speed * (self.initial_curve.forward(time) - rate)
                + self.initial_curve.slope
                + square(self.volatility) * ou_loading(2 * self.speed, time),
                name="Hull-White drift",
            ),
        )

    def diffusion(self, time: float, state: State) -> Matrix:
        nonnegative(time, "time")
        self.validate_state(state)
        return ((self.volatility,),)

    def moments(self, time: float, rate: float, dt: float) -> tuple[float, float]:
        time, state, dt, _ = step_inputs(self, time, (rate,), dt, (0.0,))
        if dt == 0:
            return state[0], 0.0
        mean = (state[0] - self.shift(time)) * math.exp(-self.speed * dt) + self.shift(time + dt)
        variance = square(self.volatility) * ou_loading(2 * self.speed, dt)
        return require_finite(mean, name="conditional mean"), nonnegative(variance, "variance")

    def exact_transition(self, time: float, state: State, dt: float, shocks: State) -> State:
        time, state, dt, shocks = step_inputs(self, time, state, dt, shocks)
        mean, variance = self.moments(time, state[0], dt)
        return self.validate_state(
            (require_finite(mean + math.sqrt(variance) * shocks[0], name="rate"),)
        )

    def bond(self, time: float, maturity: float, rate: float) -> float:
        time = nonnegative(time, "valuation time")
        maturity = nonnegative(maturity, "bond maturity")
        rate = require_finite(rate, name="rate")
        if maturity < time:
            raise ModelError("Bond maturity must not precede valuation time")
        b = ou_loading(self.speed, maturity - time)
        log_ratio = -self.initial_curve.level * (
            maturity - time
        ) - 0.5 * self.initial_curve.slope * (maturity * maturity - time * time)
        correction = 0.5 * square(self.volatility) * ou_loading(2 * self.speed, time) * b * b
        return checked_exp(log_ratio + b * (self.initial_curve.forward(time) - rate) - correction)

    def bond_call(self, expiry: float, maturity: float, strike: float) -> float:
        """Time-0 European call on a unit-nominal bond, strike paid at expiry."""
        expiry = nonnegative(expiry, "option expiry")
        maturity = nonnegative(maturity, "bond maturity")
        strike = positive(strike, "bond-option strike")
        if maturity < expiry:
            raise ModelError("Bond maturity must not precede option expiry")
        forward_pv = self.initial_curve.discount(maturity)
        strike_pv = strike * self.initial_curve.discount(expiry)
        std = (
            self.volatility
            * ou_loading(self.speed, maturity - expiry)
            * math.sqrt(ou_loading(2 * self.speed, expiry))
        )
        if std == 0:
            return max(forward_pv - strike_pv, 0.0)
        h = math.log(forward_pv / strike_pv) / std + std / 2
        n1 = 0.5 * math.erfc(-h / math.sqrt(2))
        n2 = 0.5 * math.erfc(-(h - std) / math.sqrt(2))
        return nonnegative(forward_pv * n1 - strike_pv * n2, "bond-option price")
