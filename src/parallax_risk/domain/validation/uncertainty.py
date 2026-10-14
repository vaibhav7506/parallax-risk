"""Owned independent-unit bootstrap and first-order covariance propagation."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from scipy.stats import norm

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError, NumericalError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.simulation.statistics import SamplingUnit
from parallax_risk.domain.validation.contracts import Metric
from parallax_risk.domain.xva.contracts import fingerprint


@dataclass(frozen=True, slots=True)
class IndependentObservations:
    """Caller-declared independent path/pair/scramble units, never raw dependent Sobol points."""

    metric: str
    unit: str
    values: tuple[float, ...]
    sampling_unit: SamplingUnit
    total_paths: int
    source_hash: str

    def __post_init__(self) -> None:
        require_token(self.metric)
        require_text(self.unit)
        fingerprint(self.source_hash)
        require_tuple(self.values, float, nonempty=True)
        for value in self.values:
            require_finite(value, name="independent observation")
        integer(self.total_paths, "total paths", minimum=len(self.values))
        if len(self.values) < 2:
            raise DomainValidationError("Inference needs at least two independent units")
        if self.sampling_unit not in ("iid_path", "antithetic_pair", "independent_scramble"):
            raise DomainValidationError("Independent observation convention must be declared")
        multiplier = 2 if self.sampling_unit == "antithetic_pair" else 1
        if self.sampling_unit != "independent_scramble" and self.total_paths != multiplier * len(
            self.values
        ):
            raise DomainValidationError("Path counts do not match independent units")

    @property
    def hash(self) -> str:
        return content_hash(self)


class BootstrapResampler(Protocol):
    """Inject a resampling scheme consistent with the declared independent unit."""

    @property
    def method(self) -> str: ...

    def resample(
        self, values: tuple[float, ...], key: StreamKey, replicate: int
    ) -> tuple[float, ...]: ...


@dataclass(frozen=True, slots=True)
class IidUnitResampler:
    method: str = "iid_independent_unit_empirical_resampling_PCG64DXSM"

    def resample(
        self, values: tuple[float, ...], key: StreamKey, replicate: int
    ) -> tuple[float, ...]:
        require_tuple(values, float, nonempty=True)
        for value in values:
            require_finite(value, name="resampled observation")
        integer(replicate, "bootstrap replicate", minimum=0, maximum=2**32 - 1)
        if not isinstance(key, StreamKey):
            raise DomainValidationError("Bootstrap needs an owned stream key")
        sequence = np.random.SeedSequence(
            key.seed, spawn_key=(key.stream, key.substream, replicate)
        )
        generator = np.random.Generator(np.random.PCG64DXSM(sequence))
        indices = generator.integers(0, len(values), size=len(values))
        return tuple(values[int(i)] for i in indices)


@dataclass(frozen=True, slots=True)
class UncertaintyBand:
    metric: str
    unit: str
    center: float
    lower: float
    upper: float
    confidence: float
    method: str
    evidence_hash: str
    assumptions: tuple[str, ...]
    draws: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        require_token(self.metric)
        require_text(self.unit)
        require_text(self.method)
        fingerprint(self.evidence_hash)
        confidence_level(self.confidence)
        for value in (self.center, self.lower, self.upper):
            require_finite(value, name="uncertainty band")
        if self.lower > self.upper:
            raise DomainValidationError("Uncertainty band is inverted")
        require_tuple(self.assumptions, str, nonempty=True)
        require_tuple(self.draws, float)
        for assumption in self.assumptions:
            require_text(assumption)
        for value in self.draws:
            require_finite(value, name="uncertainty draw")


def confidence_level(confidence: float) -> float:
    confidence = require_finite(confidence, name="confidence")
    if not 0 < confidence < 1:
        raise DomainValidationError("Confidence must lie strictly between zero and one")
    return confidence


def bootstrap(
    data: IndependentObservations,
    key: StreamKey,
    resampler: BootstrapResampler,
    statistic: Callable[[tuple[float, ...]], float],
    *,
    statistic_name: str,
    replicates: int = 1000,
    confidence: float = 0.95,
    maximum_draws: int = 1_000_000,
) -> UncertaintyBand:
    """Percentile interval conditional on the empirical independent-unit distribution."""
    if not isinstance(data, IndependentObservations) or not isinstance(key, StreamKey):
        raise DomainValidationError("Bootstrap requires validated observations and owned key")
    require_token(statistic_name)
    require_text(resampler.method)
    integer(replicates, "bootstrap replicates", minimum=2, maximum=2**32)
    integer(maximum_draws, "bootstrap draw budget")
    confidence = confidence_level(confidence)
    if replicates * len(data.values) > maximum_draws:
        raise DomainValidationError("Bootstrap draw budget exceeded before resampling")
    center = require_finite(statistic(data.values), name="original statistic")
    draws = []
    for i in range(replicates):
        sample = resampler.resample(data.values, key, i)
        require_tuple(sample, float)
        if len(sample) != len(data.values):
            raise DomainValidationError("Resampler must retain independent-unit sample size")
        for value in sample:
            require_finite(value, name="resampler result")
        draws.append(require_finite(statistic(sample), name="bootstrap statistic"))
    alpha = (1 - confidence) / 2
    bounds = np.quantile(np.asarray(draws), (alpha, 1 - alpha), method="linear")
    evidence = content_hash(
        (data.hash, key, resampler.method, statistic_name, replicates, confidence, tuple(draws))
    )
    return UncertaintyBand(
        data.metric,
        data.unit,
        center,
        float(bounds[0]),
        float(bounds[1]),
        confidence,
        f"percentile_linear; {resampler.method}; statistic={statistic_name}",
        evidence,
        (
            f"Conditional empirical bootstrap over {data.sampling_unit}; approximate coverage",
            "No time-grid bias, market-data uncertainty or model approval inferred",
        ),
        tuple(draws),
    )


def propagate_covariance(
    metric: Metric,
    gradient: tuple[float, ...],
    covariance: tuple[tuple[float, ...], ...],
    parameter_units: tuple[str, ...],
    source_hash: str,
    *,
    confidence: float = 0.95,
) -> UncertaintyBand:
    """Local delta-method g'C g normal band; strict symmetry and PSD, no eigenvalue repair."""
    if not isinstance(metric, Metric):
        raise DomainValidationError("Covariance propagation needs a typed metric")
    require_tuple(gradient, float, nonempty=True)
    require_tuple(covariance, tuple, nonempty=True)
    require_tuple(parameter_units, str, nonempty=True)
    fingerprint(source_hash)
    confidence = confidence_level(confidence)
    n = len(gradient)
    if len(covariance) != n or len(parameter_units) != n:
        raise DomainValidationError("Gradient, covariance and parameter units must align")
    for value, unit, row in zip(gradient, parameter_units, covariance, strict=True):
        require_finite(value, name="metric gradient")
        require_text(unit)
        require_tuple(row, float)
        if len(row) != n:
            raise DomainValidationError("Parameter covariance must be square")
        for cell in row:
            require_finite(cell, name="parameter covariance")
    matrix = np.asarray(covariance, dtype=np.float64)
    if not np.array_equal(matrix, matrix.T):
        raise DomainValidationError("Parameter covariance must be exactly symmetric")
    try:
        if np.any(np.linalg.eigvalsh(matrix) < 0):
            raise DomainValidationError("Parameter covariance must be positive semidefinite")
        with np.errstate(over="raise", invalid="raise"):
            vector = np.asarray(gradient)
            variance = require_finite(float(vector @ matrix @ vector), name="propagated variance")
            width = require_finite(
                float(norm.isf((1 - confidence) / 2)) * math.sqrt(variance),
                name="normal half-width",
            )
    except (FloatingPointError, ValueError, np.linalg.LinAlgError) as error:
        raise NumericalError("Covariance propagation is not numerically representable") from error
    return UncertaintyBand(
        metric.name,
        metric.unit,
        metric.value,
        require_finite(metric.value - width, name="lower bound"),
        require_finite(metric.value + width, name="upper bound"),
        confidence,
        "local_linear_delta_method_normal_approximation",
        content_hash((metric, gradient, covariance, parameter_units, source_hash, confidence)),
        (
            "Caller-supplied parameter covariance and local derivatives; units preserved",
            "Local normal approximation; no market parameter law or guaranteed confidence coverage",
        ),
    )
