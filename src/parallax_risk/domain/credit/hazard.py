"""Piecewise constant hazard, conditional survival and finite-horizon inversion."""

import math
from dataclasses import dataclass

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.base import nonnegative


@dataclass(frozen=True, slots=True)
class RecoveryAssumption:
    """Constant recovery fraction in [0,1]; not an estimated/default-dependent recovery."""

    fraction: float

    def __post_init__(self) -> None:
        if not 0 <= require_finite(self.fraction, name="recovery") <= 1:
            raise DomainValidationError("Recovery must lie in [0,1]")

    @property
    def loss_given_default(self) -> float:
        """Declared complement; exposure is never multiplied by this in Phase 6."""
        return 1.0 - self.fraction


@dataclass(frozen=True, slots=True)
class PiecewiseHazardCurve:
    """Hazards h_i (1/year) on [t_i,t_(i+1)), t_0=0; no extrapolation.

    Survival is conditional on alive at origin. A default on the last endpoint
    is represented; no default before that horizon is None, never infinity.
    """

    times: tuple[float, ...]
    hazards: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.times, tuple) or not isinstance(self.hazards, tuple):
            raise DomainValidationError("Hazard inputs must be immutable tuples")
        if len(self.times) < 2 or len(self.hazards) != len(self.times) - 1:
            raise DomainValidationError("Hazards require one rate per increasing interval")
        for t in self.times:
            nonnegative(t, "hazard time")
        for h in self.hazards:
            nonnegative(h, "hazard rate")
        if self.times[0] != 0 or any(
            b <= a for a, b in zip(self.times, self.times[1:], strict=False)
        ):
            raise DomainValidationError("Hazard times must start at zero and strictly increase")
        self.cumulative_hazard(self.times[-1])

    def cumulative_hazard(self, time: float) -> float:
        """Integral of the supplied hazards, with checked finite arithmetic."""
        time = nonnegative(time, "credit time")
        if time > self.times[-1]:
            raise DomainValidationError("Credit curve cannot be extrapolated")
        increments = (
            h * max(0.0, min(time, b) - a)
            for a, b, h in zip(self.times, self.times[1:], self.hazards, strict=False)
        )
        try:
            return require_finite(math.fsum(increments), name="cumulative hazard")
        except OverflowError:
            raise DomainValidationError("Cumulative hazard overflowed") from None

    def survival(self, time: float) -> float:
        """S(t)=exp(-H(t)); valid binary64 underflow to zero is declared saturation."""
        return math.exp(-self.cumulative_hazard(time))

    def default_probability(self, time: float) -> float:
        """F(t)=1-S(t), using expm1 to preserve small default probabilities."""
        return -math.expm1(-self.cumulative_hazard(time))

    def default_increment(self, start: float, end: float) -> float:
        """Unconditional interval default mass S(start)*(1-exp(-ΔH))."""
        a, b = self.cumulative_hazard(start), self.cumulative_hazard(end)
        if end < start:
            raise DomainValidationError("Default interval must be ordered")
        return math.exp(-a) * (-math.expm1(-(b - a)))

    def default_time(self, exponential_threshold: float) -> float | None:
        """Solve H(tau)=E for supplied E>0 (unit exponential under the Cox model)."""
        threshold = require_finite(exponential_threshold, name="default threshold")
        if threshold <= 0:
            raise DomainValidationError("Default threshold must be strictly positive")
        cumulative = 0.0
        for a, b, h in zip(self.times, self.times[1:], self.hazards, strict=False):
            next_value = require_finite(cumulative + h * (b - a), name="integrated default hazard")
            if h > 0 and threshold <= next_value:
                result = require_finite(a + (threshold - cumulative) / h, name="default time")
                if result <= 0:
                    raise DomainValidationError("Default time is below binary64 resolution")
                return result
            cumulative = next_value
        return None

    @property
    def hash(self) -> str:
        """Fingerprint of declared intervals/rates, independent of random draws."""
        return content_hash(self)
