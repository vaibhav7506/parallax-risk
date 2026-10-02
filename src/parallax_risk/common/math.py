"""Finite scalar arithmetic and deliberate comparison tolerances."""

import math
from dataclasses import dataclass

from parallax_risk.common.enums import Compounding
from parallax_risk.common.errors import ConventionError, NumericalError


def require_finite(value: float, *, name: str) -> float:
    """Reject non-real, boolean and non-finite numerical inputs."""
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise NumericalError(f"{name} must be a finite real scalar")
    try:
        result = float(value)
    except OverflowError:
        raise NumericalError(f"{name} cannot be represented as a finite float") from None
    if not math.isfinite(result):
        raise NumericalError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class NumericalTolerance:
    """Scalar closeness: |a-b| <= max(absolute, relative*max(|a|,|b|)).

    Defaults suit dimensionless foundation checks; monetary and Monte Carlo
    tolerances must be declared in their later model configurations.
    """

    absolute: float = 1e-12
    relative: float = 1e-9

    def __post_init__(self) -> None:
        absolute = require_finite(self.absolute, name="absolute tolerance")
        relative = require_finite(self.relative, name="relative tolerance")
        if absolute < 0 or not 0 <= relative < 1 or absolute == relative == 0:
            raise NumericalError(
                "Tolerances require absolute >= 0, 0 <= relative < 1, one positive"
            )

    def is_close(self, left: float, right: float) -> bool:
        """Compare two finite scalars; NaN/Inf never masquerade as results."""
        return math.isclose(
            require_finite(left, name="left"),
            require_finite(right, name="right"),
            rel_tol=self.relative,
            abs_tol=self.absolute,
        )


def accumulation_factor(
    rate: float,
    years: float,
    convention: Compounding,
    *,
    periods_per_year: int | None = None,
) -> float:
    """Accumulate a decimal annual rate over nonnegative year-fraction time.

    Simple: 1+r*t; continuous: exp(r*t); periodic: (1+r/m)^(m*t).
    This is a convention primitive, not a pricing or discount-curve engine.
    All factors must be positive and finite; no convention is guessed.
    """
    rate = require_finite(rate, name="annual rate")
    years = require_finite(years, name="year fraction")
    if years < 0 or not isinstance(convention, Compounding):
        raise ConventionError("Nonnegative time and an explicit compounding convention required")
    if convention != Compounding.PERIODIC and periods_per_year is not None:
        raise ConventionError("Frequency is only valid for periodic compounding")
    try:
        if convention == Compounding.SIMPLE:
            result = 1.0 + rate * years
        elif convention == Compounding.CONTINUOUS:
            result = math.exp(rate * years)
        else:
            if type(periods_per_year) is not int or periods_per_year <= 0:
                raise ConventionError("Periodic compounding requires a positive integer frequency")
            base = 1.0 + rate / periods_per_year
            if base <= 0:
                raise NumericalError("Periodic compounding requires 1+rate/frequency > 0")
            result = base ** (periods_per_year * years)
    except OverflowError:
        raise NumericalError("Compounding overflowed") from None
    if result <= 0:
        raise NumericalError("Accumulation factor must be strictly positive")
    return require_finite(result, name="accumulation factor")
