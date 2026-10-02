"""Explicit deterministic rate contracts; no schedule or market convention inference."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import PricingError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_token
from parallax_risk.domain.instruments.cashflows import AccrualPeriod, validate_schedule


def _face(value: Money) -> None:
    if not isinstance(value, Money) or value.amount < 0:
        raise PricingError("Bond face / swap notional must be nonnegative Money")


@dataclass(frozen=True, slots=True)
class ZeroCouponBond:
    """Long, default-free redemption payment, including zero notional edge case."""

    face_value: Money
    maturity: date

    def __post_init__(self) -> None:
        _face(self.face_value)
        require_date(self.maturity)


@dataclass(frozen=True, slots=True)
class FixedRateBond:
    """Long default-free coupon bond; returned NPV is dirty present value.

    Redemption occurs on the last supplied coupon payment date. There is no
    settlement-date clean-price, ex-coupon, default or optionality adjustment.
    """

    face_value: Money
    coupon_rate: float
    periods: tuple[AccrualPeriod, ...]
    day_count: DayCount

    def __post_init__(self) -> None:
        _face(self.face_value)
        object.__setattr__(
            self, "coupon_rate", require_finite(self.coupon_rate, name="bond coupon")
        )
        validate_schedule(self.periods, self.day_count)


class SwapDirection(StrEnum):
    """Fixed/floating directions, with no principal exchanges."""

    PAY_FIXED = "pay_fixed"
    RECEIVE_FIXED = "receive_fixed"


@dataclass(frozen=True, slots=True)
class InterestRateSwap:
    """Vanilla single-currency fixed versus simple index swap with explicit schedules.

    Fixing dates are supplied per floating period. Both legs cover the same
    contractual start/end; day counts, payment dates and frequencies may differ.
    """

    notional: Money
    fixed_rate: float
    fixed_periods: tuple[AccrualPeriod, ...]
    floating_periods: tuple[AccrualPeriod, ...]
    fixing_dates: tuple[date, ...]
    index: str
    fixed_day_count: DayCount
    floating_day_count: DayCount
    direction: SwapDirection
    floating_spread: float = 0.0
    floating_gearing: float = 1.0

    def __post_init__(self) -> None:
        _face(self.notional)
        require_token(self.index)
        validate_schedule(self.fixed_periods, self.fixed_day_count)
        validate_schedule(self.floating_periods, self.floating_day_count)
        if not isinstance(self.fixing_dates, tuple) or len(self.fixing_dates) != len(
            self.floating_periods
        ):
            raise PricingError("Exactly one immutable fixing date per floating period is required")
        if not isinstance(self.direction, SwapDirection):
            raise PricingError("Swap direction must be explicit")
        if (self.fixed_periods[0].start, self.fixed_periods[-1].end) != (
            self.floating_periods[0].start,
            self.floating_periods[-1].end,
        ):
            raise PricingError("Swap legs must share contractual start and end dates")
        for fixing, period in zip(self.fixing_dates, self.floating_periods, strict=True):
            require_date(fixing)
            if fixing > period.start:
                raise PricingError("Floating fixings must occur on or before accrual start")
        for name in ("fixed_rate", "floating_spread", "floating_gearing"):
            object.__setattr__(self, name, require_finite(getattr(self, name), name=name))
