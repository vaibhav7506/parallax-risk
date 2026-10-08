"""Owned default thresholds, static rank dependence and stochastic spread abstraction."""

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
from scipy.special import ndtri
from scipy.stats import rankdata

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.models.base import nonnegative
from parallax_risk.domain.simulation.arrays import FloatArray, finite_array, integer
from parallax_risk.domain.simulation.random import StreamKey


@runtime_checkable
class StochasticCreditSpread(Protocol):
    """Explicit spread-state to intensity policy; the market engine evolves its state."""

    @property
    def hash(self) -> str: ...

    @property
    def recovery(self) -> RecoveryAssumption: ...

    def intensity(self, spread: float) -> float:
        """Return finite nonnegative annual default intensity from an annual spread."""
        ...


@dataclass(frozen=True, slots=True)
class ReducedFormSpread:
    """Research credit-triangle λ=s/(1-R); not a CDS/bond calibration or exact identity."""

    recovery: RecoveryAssumption

    def __post_init__(self) -> None:
        if not isinstance(self.recovery, RecoveryAssumption) or self.recovery.fraction == 1:
            raise DomainValidationError(
                "Spread conversion requires typed recovery strictly below 1"
            )

    def intensity(self, spread: float) -> float:
        return require_finite(
            nonnegative(spread, "credit spread") / self.recovery.loss_given_default,
            name="credit intensity",
        )

    @property
    def hash(self) -> str:
        return content_hash(self)


def default_thresholds(key: StreamKey, paths: int) -> FloatArray:
    """Independent Exp(1) thresholds from a fresh explicitly addressed PCG64DXSM."""
    if not isinstance(key, StreamKey):
        raise DomainValidationError("Default sequence requires explicit StreamKey")
    integer(paths, "default path count")
    values = np.asarray(key.generator().exponential(size=paths), dtype=np.float64)
    finite_array(values, ndim=1, name="default thresholds")
    if np.any(values <= 0):
        raise DomainValidationError("Default sampler produced a nonpositive threshold")
    return values


def static_rank_thresholds(
    thresholds: FloatArray, score: FloatArray, rho: float, key: StreamKey
) -> FloatArray:
    """Gaussian rank scenario, preserving the entire sampled threshold marginal.

    Higher scores and rho>0 receive earlier defaults. rho=0 is the exact independent
    baseline. Mid-ranks handle ties. This non-adapted whole-path stress is not an
    intensity model; empirical rank dependence is not an exact population copula.
    """
    finite_array(thresholds, ndim=1, name="thresholds")
    finite_array(score, ndim=1, name="static scores")
    rho = require_finite(rho, name="static dependence")
    if thresholds.shape != score.shape or np.any(thresholds <= 0) or not -1 <= rho <= 1:
        raise DomainValidationError("Static dependence requires aligned scores/positive thresholds")
    if not isinstance(key, StreamKey):
        raise DomainValidationError("Static dependence requires explicit address")
    if rho == 0:
        return thresholds.copy()
    normals = ndtri((rankdata(score, method="average") - 0.5) / score.size)
    latent = rho * normals + math.sqrt(1 - rho * rho) * key.generator().standard_normal(score.size)
    ordered = np.argsort(latent, kind="stable")
    result = np.empty_like(thresholds)
    result[ordered] = np.sort(thresholds)[::-1]
    return result


def intensity_default_times(
    times: tuple[float, ...], intensities: FloatArray, thresholds: FloatArray
) -> tuple[float | None, ...]:
    """Left-constant predictable intensities per path; exact crossing of that discretization."""
    finite_array(intensities, ndim=2, name="path intensities")
    finite_array(thresholds, ndim=1, name="default thresholds")
    if not isinstance(times, tuple) or len(times) < 2:
        raise DomainValidationError("Intensity grid requires an immutable positive horizon")
    if intensities.shape != (thresholds.size, len(times) - 1):
        raise DomainValidationError("Intensity path shape must match interval grid and thresholds")
    return tuple(
        PiecewiseHazardCurve(times, tuple(float(h) for h in row)).default_time(float(e))
        for row, e in zip(intensities, thresholds, strict=True)
    )


def conditional_survival(times: tuple[float, ...], intensities: FloatArray) -> FloatArray:
    """Exp(-left-constant integrated intensity) conditional on each hazard path."""
    finite_array(intensities, ndim=2, name="path intensities")
    if not isinstance(times, tuple) or len(times) < 2:
        raise DomainValidationError("Intensity grid requires an immutable positive horizon")
    PiecewiseHazardCurve(times, (0.0,) * (len(times) - 1))
    if intensities.shape[1] != len(times) - 1 or np.any(intensities < 0):
        raise DomainValidationError("Intensity paths must match grid and be nonnegative")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            integrated = np.cumsum(intensities * np.diff(times), axis=1)
            return np.column_stack((np.ones(intensities.shape[0]), np.exp(-integrated)))
    except FloatingPointError:
        raise DomainValidationError("Integrated stochastic intensity overflowed") from None
