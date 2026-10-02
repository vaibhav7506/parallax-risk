"""Stateless interpolation strategies; extrapolation belongs to curve contracts."""

import math
from bisect import bisect_left
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from parallax_risk.common.errors import CurveError
from parallax_risk.common.math import require_finite


class InterpolationKind(StrEnum):
    """Linear ordinates or linear log-positive ordinates."""

    LINEAR = "linear"
    LOG_LINEAR = "log_linear"


class ExtrapolationPolicy(StrEnum):
    """No extrapolation or constant terminal zero rate, explicitly chosen."""

    ERROR = "error"
    FLAT_ZERO = "flat_zero"


class Interpolator(Protocol):
    """Typed strategy interface for interpolation inside immutable ordered nodes."""

    def interpolate(self, point: float, x: tuple[float, ...], y: tuple[float, ...]) -> float:
        """Return an interpolated ordinate; outside-domain requests raise CurveError."""
        ...


def validate_nodes(x: tuple[float, ...], y: tuple[float, ...]) -> None:
    """Require immutable, nonempty, aligned finite nodes with increasing abscissae."""
    if not isinstance(x, tuple) or not isinstance(y, tuple) or not x or len(x) != len(y):
        raise CurveError("Interpolation requires nonempty, aligned immutable node tuples")
    for value in (*x, *y):
        require_finite(value, name="curve node")
    if any(right <= left for left, right in zip(x, x[1:], strict=False)):
        raise CurveError("Curve abscissae must be strictly increasing")


def _location(point: float, x: tuple[float, ...], y: tuple[float, ...]) -> int:
    validate_nodes(x, y)
    point = require_finite(point, name="interpolation coordinate")
    if not x[0] <= point <= x[-1]:
        raise CurveError("Interpolation coordinate lies outside node range")
    return bisect_left(x, point)


@dataclass(frozen=True, slots=True)
class LinearInterpolator:
    """Piecewise linear interpolation of finite ordinates, preserving exact knots."""

    def interpolate(self, point: float, x: tuple[float, ...], y: tuple[float, ...]) -> float:
        """Interpolate y directly; both input and output must be finite."""
        index = _location(point, x, y)
        if x[index] == point:
            return y[index]
        weight = (point - x[index - 1]) / (x[index] - x[index - 1])
        result = (1.0 - weight) * y[index - 1] + weight * y[index]
        return require_finite(result, name="linear interpolation result")


@dataclass(frozen=True, slots=True)
class LogLinearInterpolator:
    """Piecewise linear log(y), appropriate for positive discount factors."""

    def interpolate(self, point: float, x: tuple[float, ...], y: tuple[float, ...]) -> float:
        """Interpolate positive ordinates geometrically without extrapolation."""
        index = _location(point, x, y)
        if any(value <= 0 for value in y):
            raise CurveError("Log-linear ordinates must be strictly positive")
        if x[index] == point:
            return y[index]
        weight = (point - x[index - 1]) / (x[index] - x[index - 1])
        result = math.exp((1.0 - weight) * math.log(y[index - 1]) + weight * math.log(y[index]))
        if result <= 0:
            raise CurveError("Log-linear interpolation underflowed")
        return require_finite(result, name="log-linear interpolation result")


def interpolator(kind: InterpolationKind) -> Interpolator:
    """Construct the declared strategy; unsupported selections fail explicitly."""
    if not isinstance(kind, InterpolationKind):
        raise CurveError("Interpolation kind must be explicit")
    if kind == InterpolationKind.LINEAR:
        return LinearInterpolator()
    return LogLinearInterpolator()
