"""Finite empirical EE/ENE/PFE/EPE and right-endpoint default exposure summaries."""

from dataclasses import dataclass

import numpy as np

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_currency
from parallax_risk.domain.simulation.arrays import FloatArray, FrozenArray, finite_array


def validate_times(times: tuple[float, ...]) -> None:
    """Strict time origin and positive horizon, in declared years."""
    if not isinstance(times, tuple) or len(times) < 2:
        raise DomainValidationError("Exposure grid needs an immutable positive horizon")
    for time in times:
        require_finite(time, name="exposure time")
    if times[0] != 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise DomainValidationError("Exposure times must start at zero and strictly increase")


@dataclass(frozen=True, slots=True)
class ExposureProfile:
    """EE positive/ENE payable magnitude; EPE is trapezoidal EE average over supplied horizon."""

    currency: Currency
    times: tuple[float, ...]
    expected_exposure: tuple[float, ...]
    expected_negative_exposure: tuple[float, ...]
    quantiles: tuple[float, ...]
    potential_future_exposure: FrozenArray
    expected_positive_exposure: float
    paths: int
    quantile_method: str = "linear_empirical"
    epe_method: str = "trapezoidal_full_supplied_horizon"


def profile(
    positive: FloatArray,
    negative: FloatArray,
    times: tuple[float, ...],
    quantiles: tuple[float, ...],
    currency: Currency,
) -> ExposureProfile:
    """Equal path weights including zero scenarios; quantiles include q=0 and q=1."""
    finite_array(positive, ndim=2, name="positive exposure")
    finite_array(negative, ndim=2, name="negative exposure magnitude")
    validate_times(times)
    require_currency(currency)
    if (
        positive.shape != negative.shape
        or positive.shape[1] != len(times)
        or np.any(positive < 0)
        or np.any(negative < 0)
    ):
        raise DomainValidationError("Exposure matrices must align and have nonnegative magnitudes")
    if not isinstance(quantiles, tuple) or not quantiles:
        raise DomainValidationError("Provide immutable nonempty PFE quantiles")
    for q in quantiles:
        if not 0 <= require_finite(q, name="PFE quantile") <= 1:
            raise DomainValidationError("PFE quantile must lie in [0,1]")
    if any(b <= a for a, b in zip(quantiles, quantiles[1:], strict=False)):
        raise DomainValidationError("PFE quantiles must strictly increase")
    with np.errstate(over="raise", invalid="raise"):
        try:
            ee = np.mean(positive, axis=0)
            ene = np.mean(negative, axis=0)
            pfe = np.quantile(positive, quantiles, axis=0, method="linear")
            epe = float(np.trapezoid(ee, np.asarray(times)) / (times[-1] - times[0]))
        except FloatingPointError:
            raise DomainValidationError("Exposure statistics overflowed") from None
    return ExposureProfile(
        currency,
        times,
        tuple(map(float, ee)),
        tuple(map(float, ene)),
        quantiles,
        FrozenArray.from_array(pfe),
        require_finite(epe, name="EPE"),
        positive.shape[0],
    )


@dataclass(frozen=True, slots=True)
class ExposureAtDefault:
    """Grid research EAD, not regulatory alpha*effective EPE or a recovered/discounted loss."""

    default_times: tuple[float | None, ...]
    bucket_times: tuple[float | None, ...]
    positive_exposures: tuple[float, ...]
    defaults: int
    default_probability: float
    mean_with_nondefault_zero: float
    mean_given_default: float | None
    approximation: str = "right_grid_endpoint_no_default_conditioned_margin_freeze"


def exposure_at_default(
    exposures: FloatArray, times: tuple[float, ...], defaults: tuple[float | None, ...]
) -> ExposureAtDefault:
    """Map defaults to the first grid endpoint >= tau; retain zero for no default.

    This uses an alive/unconditional collateral path; it does not freeze margin
    at tau or interpolate closeout within the interval. Refinement is caller work.
    """
    finite_array(exposures, ndim=2, name="default exposure paths")
    validate_times(times)
    if (
        not isinstance(defaults, tuple)
        or len(defaults) != exposures.shape[0]
        or exposures.shape[1] != len(times)
        or np.any(exposures < 0)
    ):
        raise DomainValidationError("Defaults/exposure grid must align")
    buckets: list[float | None] = []
    values: list[float] = []
    count = 0
    for path, tau in enumerate(defaults):
        if tau is None:
            buckets.append(None)
            values.append(0.0)
        else:
            tau = require_finite(tau, name="default time")
            if not 0 < tau <= times[-1]:
                raise DomainValidationError("Default time must lie in (0,horizon]")
            index = int(np.searchsorted(times, tau, side="left"))
            buckets.append(times[index])
            values.append(float(exposures[path, index]))
            count += 1
    average = require_finite(float(np.mean(values)), name="unconditional EAD mean")
    conditional = (
        require_finite(float(np.sum(values)) / count, name="conditional EAD mean")
        if count
        else None
    )
    return ExposureAtDefault(
        defaults, tuple(buckets), tuple(values), count, count / len(values), average, conditional
    )


@dataclass(frozen=True, slots=True)
class DependenceComparison:
    """Paired-scenario exposure/default diagnostics; neither discounted nor loss-adjusted."""

    baseline: ExposureAtDefault
    scenario: ExposureAtDefault
    difference_in_default_weighted_exposure: float
    ratio: float | None


def compare_dependence(
    baseline: ExposureAtDefault, scenario: ExposureAtDefault
) -> DependenceComparison:
    if (
        not isinstance(baseline, ExposureAtDefault)
        or not isinstance(scenario, ExposureAtDefault)
        or len(baseline.default_times) != len(scenario.default_times)
    ):
        raise DomainValidationError("Dependence comparison requires aligned EAD results")
    denominator = baseline.mean_with_nondefault_zero
    difference = require_finite(
        scenario.mean_with_nondefault_zero - denominator, name="WWR difference"
    )
    ratio = (
        require_finite(scenario.mean_with_nondefault_zero / denominator, name="WWR ratio")
        if denominator
        else None
    )
    return DependenceComparison(baseline, scenario, difference, ratio)
