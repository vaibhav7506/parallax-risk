"""Flat-rate/hazard linear-exposure benchmark independent of production quadrature."""

import math
from dataclasses import dataclass

from scipy.integrate import quad

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_currency, require_text, require_tuple
from parallax_risk.domain.exposure.statistics import validate_times
from parallax_risk.domain.pricing._numbers import product, total
from parallax_risk.domain.validation.contracts import Contribution, Metric, ModelOutput
from parallax_risk.domain.xva.contracts import magnitudes


@dataclass(frozen=True, slots=True)
class CvaBenchmarkCase:
    times: tuple[float, ...]
    exposure: tuple[float, ...]
    currency: Currency
    rate: float
    hazard: float
    recovery: float

    def __post_init__(self) -> None:
        validate_times(self.times)
        magnitudes(self.exposure, len(self.times), "benchmark exposure")
        require_currency(self.currency)
        require_finite(self.rate, name="continuously compounded annual decimal rate")
        if (
            require_finite(self.hazard, name="annual hazard") < 0
            or not 0 <= require_finite(self.recovery, name="recovery") <= 1
        ):
            raise DomainValidationError("Benchmark hazard/recovery outside admissible domain")
        # Ensure the supplied discount/hazard horizon is representable; no clipping.
        try:
            discounts = tuple(math.exp(-self.rate * time) for time in self.times)
        except OverflowError as error:
            raise DomainValidationError("Benchmark discount overflow") from error
        if any(v == 0 or not math.isfinite(v) for v in discounts):
            raise DomainValidationError("Benchmark discount is not representable")

    @property
    def hash(self) -> str:
        return content_hash(self)


def benchmark_output(case: CvaBenchmarkCase, name: str, value: float, method: str) -> ModelOutput:
    metric = Metric("CVA", value, case.currency.value, (Contribution("credit", value),))
    return ModelOutput(
        case.hash,
        name,
        "0.9.0",
        (metric,),
        content_hash((case.hash, name, value, method)),
        (
            "Independent flat annual hazard; deterministic continuous discount; ACT/365F years",
            method,
        ),
    )


@dataclass(frozen=True, slots=True)
class IndependentCvaBenchmark:
    """Analytical constant EE; independent adaptive integral for piecewise-linear EE."""

    def evaluate(self, case: CvaBenchmarkCase) -> ModelOutput:
        if not isinstance(case, CvaBenchmarkCase):
            raise DomainValidationError("Benchmark requires a validated CVA case")
        h, r, lgd = case.hazard, case.rate, 1 - case.recovery
        if h == 0 or lgd == 0 or all(x == 0 for x in case.exposure):
            value, method = 0.0, "analytical_zero_loss"
        elif len(set(case.exposure)) == 1:
            speed = require_finite(r + h, name="discount plus hazard")
            horizon = case.times[-1]
            try:
                weight = horizon if speed == 0 else -math.expm1(-speed * horizon) / speed
            except OverflowError as error:
                raise DomainValidationError("Analytical CVA overflow") from error
            value = -product(lgd, h, case.exposure[0], weight)
            method = "analytical_constant_EE_LGD_hazard_integral_exp_minus_rate_plus_hazard"
        else:
            losses = []
            for a, b, ea, eb in zip(
                case.times, case.times[1:], case.exposure, case.exposure[1:], strict=False
            ):

                def integrand(
                    time: float, a: float = a, b: float = b, ea: float = ea, eb: float = eb
                ) -> float:
                    exposure = ea * (b - time) / (b - a) + eb * (time - a) / (b - a)
                    return product(lgd, h, exposure, math.exp(-(r + h) * time))

                integral, integration_error = quad(integrand, a, b, epsabs=1e-11, epsrel=1e-11)
                if require_finite(integration_error, name="quadrature error") > 1e-10 * max(
                    1.0, abs(integral)
                ):
                    raise DomainValidationError(
                        "Independent quadrature did not meet its error criterion"
                    )
                losses.append(require_finite(integral, name="independent integral"))
            value, method = (
                -total(tuple(losses)),
                "independent_scipy_quad_each_linear_EE_segment_1e-11",
            )
        return benchmark_output(case, "independent-cva", value, method)


@dataclass(frozen=True, slots=True)
class FlatHazardProbabilityProblem:
    """Calibrate one flat annual hazard to supplied cumulative default probabilities."""

    times: tuple[float, ...]
    observed: tuple[float, ...]
    scales: tuple[float, ...]
    source: str

    def __post_init__(self) -> None:
        require_tuple(self.times, float, nonempty=True)
        require_tuple(self.observed, float, nonempty=True)
        require_tuple(self.scales, float, nonempty=True)
        require_text(self.source)
        if len(self.times) != len(self.observed) or len(self.scales) != len(self.times):
            raise DomainValidationError("Probability calibration points and scales must align")
        if any(require_finite(t, name="probability time") <= 0 for t in self.times) or any(
            b <= a for a, b in zip(self.times, self.times[1:], strict=False)
        ):
            raise DomainValidationError(
                "Probability calibration times must be positive and increasing"
            )
        if any(not 0 <= require_finite(p, name="observed probability") < 1 for p in self.observed):
            raise DomainValidationError("Observed probability must lie in [0,1)")
        if any(require_finite(s, name="probability residual scale") <= 0 for s in self.scales):
            raise DomainValidationError("Probability residual scales must be positive")

    @property
    def model_name(self) -> str:
        return "flat-hazard-probability"

    @property
    def model_version(self) -> str:
        return "0.9.0"

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return ("hazard",)

    @property
    def value_unit(self) -> str:
        return "cumulative_default_probability_fraction"

    @property
    def input_hash(self) -> str:
        return content_hash(self)

    def predict(self, parameters: tuple[float, ...]) -> tuple[float, ...]:
        require_tuple(parameters, float)
        if len(parameters) != 1 or require_finite(parameters[0], name="flat hazard") < 0:
            raise DomainValidationError(
                "Flat probability model requires one nonnegative annual hazard"
            )
        return tuple(-math.expm1(-product(parameters[0], time)) for time in self.times)
