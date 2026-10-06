"""Analytical reference moments for the production GBM research experiments."""

import math

from parallax_risk.common.errors import NumericalError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.base import checked_exp, nonnegative, positive, square


def gbm_terminal_moments(
    model: GeometricBrownianMotion, spot: float, horizon: float
) -> tuple[float, float]:
    spot = positive(spot, "initial spot")
    horizon = nonnegative(horizon, "horizon")
    mean = require_finite(spot * checked_exp(model.drift_rate * horizon), name="GBM mean")
    try:
        variance = square(mean) * math.expm1(square(model.volatility) * horizon)
    except OverflowError as error:
        raise NumericalError("GBM reference variance overflowed") from error
    return mean, nonnegative(variance, "GBM variance")


def gbm_call_expectation(
    model: GeometricBrownianMotion, spot: float, horizon: float, strike: float
) -> float:
    """Undiscounted E[(S_T-K)+], under the caller's drift; no measure is inferred."""
    strike = positive(strike, "strike")
    mean, _ = gbm_terminal_moments(model, spot, horizon)
    std = model.volatility * math.sqrt(horizon)
    if std == 0:
        return max(mean - strike, 0.0)
    d1 = (math.log(mean) - math.log(strike) + 0.5 * square(std)) / std
    n1 = 0.5 * math.erfc(-d1 / math.sqrt(2))
    n2 = 0.5 * math.erfc(-(d1 - std) / math.sqrt(2))
    return nonnegative(mean * n1 - strike * n2, "GBM positive-part expectation")
