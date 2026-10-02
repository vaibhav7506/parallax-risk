"""Discount, zero and simple-forward curves with declared financial conventions."""

import math
from dataclasses import dataclass, replace
from datetime import date

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.errors import CurveError, MissingMarketDataError, NumericalError
from parallax_risk.common.identifiers import CurveId
from parallax_risk.common.math import accumulation_factor, require_finite
from parallax_risk.common.time import require_date, year_fraction
from parallax_risk.domain._validation import (
    positive_accrual,
    require_currency,
    require_token,
    require_tuple,
)
from parallax_risk.domain.market.curves.interpolation import (
    ExtrapolationPolicy,
    InterpolationKind,
    interpolator,
    validate_nodes,
)


def _curve_contract(
    curve_id: CurveId,
    currency: Currency,
    valuation_date: date,
    day_count: DayCount,
    times: tuple[float, ...],
    values: tuple[float, ...],
    extrapolation: ExtrapolationPolicy,
) -> None:
    if not isinstance(curve_id, CurveId):
        raise CurveError("A typed CurveId is required")
    require_currency(currency)
    require_date(valuation_date)
    if not isinstance(day_count, DayCount) or not isinstance(extrapolation, ExtrapolationPolicy):
        raise CurveError("Curve day count and extrapolation must be explicitly declared")
    validate_nodes(times, values)
    if len(times) < 2 or times[0] != 0:
        raise CurveError("Curve requires a t=0 anchor and at least one positive-time node")


def curve_time(value: date | float, valuation_date: date, day_count: DayCount) -> float:
    """Convert a future civil date or nonnegative year coordinate to curve time."""
    if isinstance(value, date):
        require_date(value)
        if value < valuation_date:
            raise CurveError("Curve date cannot precede valuation date")
        result = year_fraction(valuation_date, value, day_count)
    else:
        result = require_finite(value, name="curve time")
    if result < 0:
        raise CurveError("Curve time cannot be negative")
    return result


@dataclass(frozen=True, slots=True)
class DiscountCurve:
    """Positive D(0,t), with exact (0,1) anchor and explicit interpolation/extrapolation.

    Increasing discounts are allowed for negative rates. FLAT_ZERO means terminal
    continuously compounded zero-rate extrapolation, not a constant discount.
    """

    curve_id: CurveId
    currency: Currency
    valuation_date: date
    day_count: DayCount
    times: tuple[float, ...]
    discount_factors: tuple[float, ...]
    interpolation: InterpolationKind
    extrapolation: ExtrapolationPolicy

    def __post_init__(self) -> None:
        _curve_contract(
            self.curve_id,
            self.currency,
            self.valuation_date,
            self.day_count,
            self.times,
            self.discount_factors,
            self.extrapolation,
        )
        interpolator(self.interpolation)
        if self.discount_factors[0] != 1 or any(value <= 0 for value in self.discount_factors):
            raise CurveError("Discounts must be positive with D(0)=1 exactly")
        object.__setattr__(self, "times", tuple(float(value) for value in self.times))
        object.__setattr__(
            self, "discount_factors", tuple(float(value) for value in self.discount_factors)
        )

    @property
    def curve_hash(self) -> str:
        """Digest of identity, nodes and all curve conventions."""
        return content_hash(self)

    def discount(self, value: date | float) -> float:
        """Return D(0,t); terminal extrapolation is used only when explicitly selected."""
        time = curve_time(value, self.valuation_date, self.day_count)
        if time <= self.times[-1]:
            result = interpolator(self.interpolation).interpolate(
                time, self.times, self.discount_factors
            )
            if result <= 0:
                raise NumericalError("Discount interpolation underflowed")
            return result
        if self.extrapolation == ExtrapolationPolicy.ERROR:
            raise CurveError("Discount request exceeds curve horizon and extrapolation is disabled")
        exponent = math.log(self.discount_factors[-1]) * (time / self.times[-1])
        try:
            result = math.exp(exponent)
        except OverflowError:
            raise NumericalError("Discount extrapolation overflowed") from None
        if result <= 0:
            raise NumericalError("Discount extrapolation underflowed")
        return require_finite(result, name="extrapolated discount")

    def continuous_zero_rate(self, value: date | float) -> float:
        """Return -log(D)/t; a zero-time rate is intentionally undefined."""
        time = curve_time(value, self.valuation_date, self.day_count)
        if time == 0:
            raise CurveError("Continuous zero rate requires strictly positive time")
        return require_finite(-math.log(self.discount(time)) / time, name="continuous zero rate")

    def bumped(self, shift: float) -> "DiscountCurve":
        """Parallel continuous-zero shift at knots, retaining the declared interpolation.

        Log-linear D interpolation preserves an exact parallel shift between knots;
        linear-D interpolation gives a knot-based shift, explicitly not quote DV01.
        """
        shift = require_finite(shift, name="continuous zero-rate shift")
        factors = []
        for time, discount in zip(self.times, self.discount_factors, strict=True):
            try:
                value = discount * math.exp(-shift * time)
            except OverflowError:
                raise NumericalError("Curve bump overflowed") from None
            if value <= 0:
                raise NumericalError("Curve bump underflowed")
            factors.append(require_finite(value, name="bumped discount"))
        return replace(self, discount_factors=tuple(factors))


@dataclass(frozen=True, slots=True)
class ZeroCurve:
    """Piecewise linear annual zero rates with declared compounding and time units."""

    curve_id: CurveId
    currency: Currency
    valuation_date: date
    day_count: DayCount
    times: tuple[float, ...]
    rates: tuple[float, ...]
    compounding: Compounding
    extrapolation: ExtrapolationPolicy
    periods_per_year: int | None = None

    def __post_init__(self) -> None:
        _curve_contract(
            self.curve_id,
            self.currency,
            self.valuation_date,
            self.day_count,
            self.times,
            self.rates,
            self.extrapolation,
        )
        for time, rate in zip(self.times, self.rates, strict=True):
            accumulation_factor(
                rate, time, self.compounding, periods_per_year=self.periods_per_year
            )
        object.__setattr__(self, "times", tuple(float(value) for value in self.times))
        object.__setattr__(self, "rates", tuple(float(value) for value in self.rates))

    def zero_rate(self, value: date | float) -> float:
        """Interpolate rates linearly; FLAT_ZERO holds the terminal quoted zero rate."""
        time = curve_time(value, self.valuation_date, self.day_count)
        if time > self.times[-1]:
            if self.extrapolation == ExtrapolationPolicy.ERROR:
                raise CurveError("Zero-rate request exceeds horizon and extrapolation is disabled")
            return self.rates[-1]
        return interpolator(InterpolationKind.LINEAR).interpolate(time, self.times, self.rates)

    def discount(self, value: date | float) -> float:
        """Derive D from the interpolated zero rate using the explicit compounding."""
        time = curve_time(value, self.valuation_date, self.day_count)
        result = 1.0 / accumulation_factor(
            self.zero_rate(time),
            time,
            self.compounding,
            periods_per_year=self.periods_per_year,
        )
        if result <= 0:
            raise NumericalError("Zero-curve discount underflowed")
        return require_finite(result, name="zero-curve discount")

    def to_discount_curve(
        self, *, interpolation: InterpolationKind, extrapolation: ExtrapolationPolicy
    ) -> DiscountCurve:
        """Sample zero-curve knot discounts into a separately declared discount representation.

        Interpolation between knots may change; this conversion never promises
        equality of the two continuous representations away from their knots.
        """
        return DiscountCurve(
            self.curve_id,
            self.currency,
            self.valuation_date,
            self.day_count,
            self.times,
            tuple(self.discount(time) for time in self.times),
            interpolation,
            extrapolation,
        )


@dataclass(frozen=True, slots=True)
class ForwardCurve:
    """Explicit index projection curve; may differ from its currency's discount curve."""

    index: str
    curve: DiscountCurve

    def __post_init__(self) -> None:
        require_token(self.index)
        if not isinstance(self.curve, DiscountCurve):
            raise CurveError("Forward projection requires an explicit DiscountCurve")

    def simple_rate(self, start: date, end: date, day_count: DayCount) -> float:
        """Simple annual forward (D(start)/D(end)-1)/accrual for the given index."""
        accrual = positive_accrual(start, end, day_count)
        ratio = require_finite(
            self.curve.discount(start) / self.curve.discount(end), name="forward discount ratio"
        )
        if ratio <= 0:
            raise NumericalError("Forward discount ratio underflowed")
        return require_finite((ratio - 1.0) / accrual, name="simple forward rate")


@dataclass(frozen=True, slots=True)
class CurveSet:
    """Immutable currency discount and currency/index projection assignments."""

    discount_curves: tuple[DiscountCurve, ...]
    forward_curves: tuple[ForwardCurve, ...] = ()

    def __post_init__(self) -> None:
        require_tuple(self.discount_curves, DiscountCurve, nonempty=True)
        require_tuple(self.forward_curves, ForwardCurve)
        if len({curve.currency for curve in self.discount_curves}) != len(self.discount_curves):
            raise CurveError("One discount curve per currency is required")
        keys = {(forward.curve.currency, forward.index) for forward in self.forward_curves}
        if len(keys) != len(self.forward_curves):
            raise CurveError("One projection curve per currency/index is required")
        all_curves = (*self.discount_curves, *(forward.curve for forward in self.forward_curves))
        if len({curve.valuation_date for curve in all_curves}) != 1:
            raise CurveError("All curves must share the same valuation date")
        for curve in all_curves:
            if any(other.curve_id == curve.curve_id and other != curve for other in all_curves):
                raise CurveError("A CurveId cannot identify inconsistent curve content")
        object.__setattr__(
            self,
            "discount_curves",
            tuple(sorted(self.discount_curves, key=lambda item: item.currency)),
        )
        object.__setattr__(
            self,
            "forward_curves",
            tuple(sorted(self.forward_curves, key=lambda item: (item.curve.currency, item.index))),
        )

    @property
    def curve_hash(self) -> str:
        """Digest of curve content and index/currency assignments."""
        return content_hash(self)

    def discount_curve(self, currency: Currency) -> DiscountCurve:
        """Look up an explicit currency discount curve; no fallback to projection."""
        require_currency(currency)
        for curve in self.discount_curves:
            if curve.currency == currency:
                return curve
        raise MissingMarketDataError("Required currency discount curve is absent")

    def forward_curve(self, currency: Currency, index: str) -> ForwardCurve:
        """Look up an explicit projection curve; no fallback to discounting."""
        require_currency(currency)
        require_token(index)
        for forward in self.forward_curves:
            if (forward.curve.currency, forward.index) == (currency, index):
                return forward
        raise MissingMarketDataError("Required index projection curve is absent")

    def bumped(self, curve_ids: tuple[CurveId, ...], shift: float) -> "CurveSet":
        """Bump only explicitly named curves, including all assignments of shared IDs."""
        require_tuple(curve_ids, CurveId, nonempty=True)
        present = {curve.curve_id for curve in self.discount_curves} | {
            forward.curve.curve_id for forward in self.forward_curves
        }
        if len(set(curve_ids)) != len(curve_ids) or not set(curve_ids) <= present:
            raise CurveError("Bump IDs must be unique and present in curve set")
        return CurveSet(
            tuple(
                curve.bumped(shift) if curve.curve_id in curve_ids else curve
                for curve in self.discount_curves
            ),
            tuple(
                replace(forward, curve=forward.curve.bumped(shift))
                if forward.curve.curve_id in curve_ids
                else forward
                for forward in self.forward_curves
            ),
        )
