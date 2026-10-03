"""European Heston calls by Lewis Fourier inversion, with explicit integration gates."""

import cmath
import math
from dataclasses import dataclass

from scipy.integrate import quad

from parallax_risk.common.errors import NumericalError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.base import checked_exp, nonnegative, ou_loading, positive, square


@dataclass(frozen=True, slots=True)
class FourierSettings:
    """Price currency-unit error gate, quadrature relative tolerance and interval limit."""

    absolute_price_tolerance: float = 1e-7
    relative_tolerance: float = 1e-9
    subdivision_limit: int = 250

    def __post_init__(self) -> None:
        positive(self.absolute_price_tolerance, "absolute price tolerance")
        positive(self.relative_tolerance, "quadrature relative tolerance")
        if self.relative_tolerance >= 1:
            raise NumericalError("Quadrature relative tolerance must be below one")
        if type(self.subdivision_limit) is not int or self.subdivision_limit < 2:
            raise NumericalError("Quadrature subdivision limit must be an integer >=2")


@dataclass(frozen=True, slots=True)
class HestonCallPrice:
    value: float
    estimated_absolute_error: float
    integrand_evaluations: int
    method: str
    feller_margin: float


_DEFAULT_FOURIER_SETTINGS = FourierSettings()


def _complex_log1p(value: complex) -> complex:
    """Cancellation-safe log(1+z); 8-term series for |z|<1e-4 (error O(|z|^9))."""
    if abs(value) >= 1e-4:
        return cmath.log(1 + value)
    term = value
    result = value
    for order in range(2, 9):
        term *= -value
        result += term / order
    return result


def _complex_expm1(value: complex) -> complex:
    """Cancellation-safe exp(z)-1, matching the log1p series error policy."""
    if abs(value) >= 1e-4:
        return cmath.exp(value) - 1
    term = value
    result = value
    for order in range(2, 9):
        term *= value / order
        result += term
    return result


def characteristic_function(
    model: Heston, spot: float, variance: float, time: float, u: complex
) -> complex:
    """E_Q[exp(i*u*log S_T)], stable decaying-exponential Riccati representation.

    Pricing uses Im(u)=-1/2, inside the moment strip. Other complex moments are
    not guaranteed; no exponential moment-domain certification is implemented.
    """
    spot, variance = model.validate_state((spot, variance))
    time = nonnegative(time, "option time")
    require_finite(u.real, name="Fourier real argument")
    require_finite(u.imag, name="Fourier imaginary argument")
    iu = 1j * u
    try:
        if time == 0:
            exponent = iu * math.log(spot)
        elif model.vol_of_variance == 0:
            integrated = model.variance_level * time + (
                variance - model.variance_level
            ) * ou_loading(model.speed, time)
            exponent = (
                iu * (math.log(spot) + (model.rate - model.dividend) * time)
                - 0.5 * (u * u + iu) * integrated
            )
        else:
            xi2 = square(model.vol_of_variance)
            beta = model.speed - model.correlation * model.vol_of_variance * iu
            d = cmath.sqrt(beta * beta + xi2 * (u * u + iu))
            # Rationalize beta-d, so xi -> 0 does not subtract close square roots.
            h = (u * u + iu) / (beta + d)
            g = -xi2 * h / (beta + d)
            one_minus_decay = -_complex_expm1(-d * time)
            decay = 1 - one_minus_decay
            log_ratio = _complex_log1p(g * one_minus_decay / (1 - g))
            c = model.speed * model.variance_level * (-h * time - 2 * log_ratio / xi2)
            loading = -h * one_minus_decay / (1 - g * decay)
            exponent = (
                iu * (math.log(spot) + (model.rate - model.dividend) * time)
                + c
                + loading * variance
            )
        result = cmath.exp(exponent)
    except (OverflowError, ZeroDivisionError, ValueError) as error:
        raise NumericalError("Heston characteristic function could not be evaluated") from error
    require_finite(result.real, name="characteristic real part")
    require_finite(result.imag, name="characteristic imaginary part")
    return result


def heston_call(
    model: Heston,
    spot: float,
    variance: float,
    strike: float,
    expiry: float,
    settings: FourierSettings = _DEFAULT_FOURIER_SETTINGS,
) -> HestonCallPrice:
    """Undiscounted spot, continuous r/q, European call per one underlying unit.

    Integrates [0,infinity). QUADPACK failure or excessive price-scaled estimated
    error raises NumericalError. Error is an estimate, not a rigorous tail bound.
    Exact xi=0 and absorbing zero-variance boundaries use the Gaussian limit.
    """
    spot, variance = model.validate_state((spot, variance))
    strike = positive(strike, "option strike")
    expiry = nonnegative(expiry, "option expiry")
    if not isinstance(settings, FourierSettings):
        raise NumericalError("Explicit FourierSettings are required")
    spot_pv = positive(spot * checked_exp(-model.dividend * expiry), "discounted spot")
    strike_pv = positive(strike * checked_exp(-model.rate * expiry), "discounted strike")
    if expiry == 0:
        return HestonCallPrice(
            max(spot - strike, 0.0), 0.0, 0, "expiry_intrinsic", model.feller_margin
        )
    if model.vol_of_variance == 0 or variance == model.variance_level == 0:
        integrated = nonnegative(
            model.variance_level * expiry
            + (variance - model.variance_level) * ou_loading(model.speed, expiry),
            "integrated deterministic variance",
        )
        if integrated == 0:
            price = max(spot_pv - strike_pv, 0.0)
        else:
            root = math.sqrt(integrated)
            d1 = (math.log(spot_pv / strike_pv) + integrated / 2) / root
            d2 = d1 - root
            price = spot_pv * 0.5 * math.erfc(-d1 / math.sqrt(2)) - strike_pv * 0.5 * math.erfc(
                -d2 / math.sqrt(2)
            )
        return HestonCallPrice(
            nonnegative(price, "Gaussian call"),
            0.0,
            0,
            "deterministic_variance",
            model.feller_margin,
        )
    scale = positive(
        checked_exp(-model.rate * expiry) * math.sqrt(strike) / math.pi, "Fourier price scale"
    )

    def integrand(u: float) -> float:
        cf = characteristic_function(model, spot, variance, expiry, complex(u, -0.5))
        return require_finite(
            (cmath.exp(-1j * u * math.log(strike)) * cf).real / (u * u + 0.25),
            name="Fourier integrand",
        )

    output = quad(
        integrand,
        0.0,
        math.inf,
        epsabs=settings.absolute_price_tolerance / scale,
        epsrel=settings.relative_tolerance,
        limit=settings.subdivision_limit,
        full_output=1,
    )
    if len(output) != 3:
        raise NumericalError("Heston Fourier quadrature failed convergence; no fallback applied")
    integral, error, info = output
    estimated = nonnegative(float(error) * scale, "quadrature price error")
    price = require_finite(spot_pv - scale * float(integral), name="Heston call price")
    if estimated > settings.absolute_price_tolerance:
        raise NumericalError("Heston quadrature price error exceeds the configured tolerance")
    lower = max(spot_pv - strike_pv, 0.0)
    if not lower <= price <= spot_pv:
        raise NumericalError(
            "Heston call violates European no-arbitrage bounds; no clipping applied"
        )
    return HestonCallPrice(
        price, estimated, int(info["neval"]), "lewis_infinite_quadrature", model.feller_margin
    )
