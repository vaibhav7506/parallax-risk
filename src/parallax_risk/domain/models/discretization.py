"""Explicit numerical schemes; supplied shocks only, no RNG or path generation."""

import math
from dataclasses import dataclass

from parallax_risk.common.errors import ModelError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.base import (
    ExactProcess,
    State,
    StochasticProcess,
    checked_exp,
    step_inputs,
    vector,
)


@dataclass(frozen=True, slots=True)
class EulerMaruyama:
    """X_next=X+b*dt+sigma*sqrt(dt)*Z; invalid output is rejected, never clipped.

    Strong order 1/2, weak order 1 under usual Lipschitz/smoothness hypotheses.
    Heston's square-root boundary does not satisfy those hypotheses.
    """

    def step(
        self, process: StochasticProcess, time: float, state: State, dt: float, shocks: State
    ) -> State:
        time, state, dt, shocks = step_inputs(process, time, state, dt, shocks)
        if dt == 0:
            return state
        drift = vector(process.drift(time, state), process.state_dimension, "drift")
        diffusion = process.diffusion(time, state)
        if not isinstance(diffusion, tuple) or len(diffusion) != process.state_dimension:
            raise ModelError("Diffusion row count must match the state dimension")
        rows = tuple(vector(row, process.driver_dimension, "diffusion row") for row in diffusion)
        proposal = tuple(
            require_finite(
                x
                + b * dt
                + math.sqrt(dt)
                * math.fsum(loading * z for loading, z in zip(row, shocks, strict=True)),
                name="Euler proposal",
            )
            for x, b, row in zip(state, drift, rows, strict=True)
        )
        return process.validate_state(proposal)


@dataclass(frozen=True, slots=True)
class ExactTransition:
    """Request a supported analytical one-step transition; no Euler fallback."""

    def step(
        self, process: StochasticProcess, time: float, state: State, dt: float, shocks: State
    ) -> State:
        if not isinstance(process, ExactProcess):
            raise ModelError("This process has no analytical transition implementation")
        return process.exact_transition(time, state, dt, shocks)


@dataclass(frozen=True, slots=True)
class HestonStep:
    """Explicit report of the positivity projection used by the Heston scheme."""

    state: State
    variance_proposal: float
    variance_projected: bool


@dataclass(frozen=True, slots=True)
class HestonProjectedEuler:
    """Log-Euler spot, projected Euler variance; NOT the full-truncation scheme.

    v_next=max(0,v+k(theta-v)dt+xi sqrt(v dt) Z_v). Projection introduces bias;
    no generic weak/strong order is asserted at the square-root boundary.
    """

    def step_with_diagnostics(
        self, process: StochasticProcess, time: float, state: State, dt: float, shocks: State
    ) -> HestonStep:
        if not isinstance(process, Heston):
            raise ModelError("HestonProjectedEuler requires a Heston process")
        _, state, dt, shocks = step_inputs(process, time, state, dt, shocks)
        spot, variance = state
        root = math.sqrt(variance * dt)
        zv = process.correlation * shocks[0] + math.sqrt(1 - process.correlation**2) * shocks[1]
        proposal = require_finite(
            variance
            + process.speed * (process.variance_level - variance) * dt
            + process.vol_of_variance * root * zv,
            name="variance proposal",
        )
        spot_next = require_finite(
            spot
            * checked_exp(
                (process.rate - process.dividend - 0.5 * variance) * dt + root * shocks[0]
            ),
            name="spot proposal",
        )
        output = process.validate_state((spot_next, max(0.0, proposal)))
        return HestonStep(output, proposal, proposal < 0.0)

    def step(
        self, process: StochasticProcess, time: float, state: State, dt: float, shocks: State
    ) -> State:
        return self.step_with_diagnostics(process, time, state, dt, shocks).state
