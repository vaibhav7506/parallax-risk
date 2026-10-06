"""Streaming centered moments and inference over explicitly independent sampling units."""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import t

from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.simulation.arrays import FloatArray, finite_array, integer

type SamplingUnit = Literal["iid_path", "antithetic_pair", "independent_scramble"]


@dataclass(frozen=True, slots=True)
class Estimate:
    mean: float
    sample_variance: float
    standard_error: float
    confidence: float
    confidence_interval: tuple[float, float]
    independent_units: int
    total_paths: int
    sampling_unit: SamplingUnit
    interval_method: str = "Student_t_approximation_for_independent_units"


class OnlineMoments:
    """Chan/Welford centered merging; mutable accumulator owned by one workflow."""

    def __init__(self) -> None:
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, values: FloatArray) -> None:
        finite_array(values, ndim=1, name="observations")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                count = values.size
                mean = float(np.mean(values))
                centered = values - mean
                m2 = float(np.sum(centered * centered))
                total = self.count + count
                delta = mean - self.mean
                merged_mean = mean if self.count == 0 else self.mean + delta * (count / total)
                merged_m2 = (
                    m2
                    if self.count == 0
                    else self.m2 + m2 + delta * delta * (self.count / total) * count
                )
                require_finite(merged_mean, name="sample mean")
                require_finite(merged_m2, name="centered sum of squares")
        except FloatingPointError as error:
            raise NumericalError("Sample moments overflowed") from error
        self.count, self.mean, self.m2 = total, merged_mean, merged_m2

    @property
    def variance(self) -> float:
        if self.count < 2:
            raise SimulationError("Sample variance requires at least two observations")
        return require_finite(self.m2 / (self.count - 1), name="sample variance")

    def estimate(
        self, *, total_paths: int, sampling_unit: SamplingUnit, confidence: float = 0.95
    ) -> Estimate:
        confidence = require_finite(confidence, name="confidence level")
        if not 0 < confidence < 1:
            raise SimulationError("Confidence level must be strictly between zero and one")
        integer(total_paths, "total paths", minimum=self.count)
        if sampling_unit not in ("iid_path", "antithetic_pair", "independent_scramble"):
            raise SimulationError("Independent sampling units must be explicitly identified")
        if sampling_unit == "iid_path" and total_paths != self.count:
            raise SimulationError("IID path count must equal the observation count")
        if sampling_unit == "antithetic_pair" and total_paths != 2 * self.count:
            raise SimulationError("Each antithetic observation must represent two paths")
        variance = self.variance
        error = math.sqrt(variance / self.count)
        # Avoid rounding (1+confidence)/2 up to exactly one.
        critical = require_finite(
            float(t.isf((1 - confidence) / 2, self.count - 1)), name="t quantile"
        )
        width = require_finite(critical * error, name="interval half-width")
        interval = (
            require_finite(self.mean - width, name="lower confidence bound"),
            require_finite(self.mean + width, name="upper confidence bound"),
        )
        return Estimate(
            self.mean, variance, error, confidence, interval, self.count, total_paths, sampling_unit
        )


def sampling_units(values: FloatArray, *, antithetic: bool) -> FloatArray:
    finite_array(values, ndim=1, name="path values")
    if not isinstance(antithetic, bool):
        raise SimulationError("Antithetic sampling-unit selection must be boolean")
    if not antithetic:
        return values
    if values.size % 2:
        raise SimulationError("Antithetic values must retain complete adjacent pairs")
    return 0.5 * values[0::2] + 0.5 * values[1::2]


def independent_scramble_estimate(
    replicate_means: FloatArray, *, paths_per_replicate: int, confidence: float = 0.95
) -> Estimate:
    """Approximate t interval across independent randomized quadrature replicates."""
    integer(paths_per_replicate, "paths per scramble")
    moments = OnlineMoments()
    moments.update(replicate_means)
    return moments.estimate(
        total_paths=paths_per_replicate * replicate_means.size,
        sampling_unit="independent_scramble",
        confidence=confidence,
    )
