"""Fixed and simple-index cash flows; schedules are caller-supplied civil dates."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import PricingError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import positive_accrual, require_token, require_tuple


@dataclass(frozen=True, slots=True)
class AccrualPeriod:
    """Unadjusted accrual bounds and separately declared adjusted payment date."""

    start: date
    end: date
    payment_date: date

    def __post_init__(self) -> None:
        for value in (self.start, self.end, self.payment_date):
            require_date(value)
        if self.end <= self.start or self.payment_date < self.end:
            raise PricingError("Accrual must increase and payment cannot precede accrual end")


def validate_schedule(periods: tuple[AccrualPeriod, ...], day_count: DayCount) -> None:
    """Require contiguous, nonempty accrual periods with strictly increasing payments."""
    require_tuple(periods, AccrualPeriod, nonempty=True)
    for period in periods:
        positive_accrual(period.start, period.end, day_count)
    for left, right in zip(periods, periods[1:], strict=False):
        if left.end != right.start or left.payment_date >= right.payment_date:
            raise PricingError("Coupon schedule must be contiguous with increasing payment dates")


@dataclass(frozen=True, slots=True)
class CashFlow:
    """Known signed payment; positive means receive, negative means pay."""

    payment_date: date
    amount: Money

    def __post_init__(self) -> None:
        require_date(self.payment_date)
        if not isinstance(self.amount, Money):
            raise PricingError("Cash flow amount must be Money")


@dataclass(frozen=True, slots=True)
class FixedRateCashFlow:
    """Simple coupon N*r*alpha; signed notional encodes receive/pay direction."""

    notional: Money
    rate: float
    period: AccrualPeriod
    day_count: DayCount

    def __post_init__(self) -> None:
        if not isinstance(self.notional, Money) or not isinstance(self.period, AccrualPeriod):
            raise PricingError("Fixed coupon requires Money notional and an accrual period")
        object.__setattr__(self, "rate", require_finite(self.rate, name="fixed coupon rate"))
        positive_accrual(self.period.start, self.period.end, self.day_count)


class FloatingCashFlow(Protocol):
    """Boundary for future floating coupon types; Phase 2 supports simple index coupons."""

    @property
    def notional(self) -> Money:
        """Signed notional."""
        ...

    @property
    def period(self) -> AccrualPeriod:
        """Declared accrual/payment period."""
        ...

    @property
    def fixing_date(self) -> date:
        """Index observation date."""
        ...


@dataclass(frozen=True, slots=True)
class FloatingRateCashFlow:
    """Simple coupon N*(gearing*L+spread)*alpha, fixed in advance.

    If fixing_date <= valuation date, a known fixing is mandatory. Otherwise an
    explicitly assigned index projection curve determines L. No compounding,
    in-arrears convexity or payment-lag adjustment is inferred.
    """

    notional: Money
    period: AccrualPeriod
    fixing_date: date
    index: str
    day_count: DayCount
    spread: float = 0.0
    gearing: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.notional, Money) or not isinstance(self.period, AccrualPeriod):
            raise PricingError("Floating coupon requires Money notional and an accrual period")
        require_date(self.fixing_date)
        require_token(self.index)
        positive_accrual(self.period.start, self.period.end, self.day_count)
        if self.fixing_date > self.period.start:
            raise PricingError("Phase 2 simple index coupons must fix on or before accrual start")
        object.__setattr__(self, "spread", require_finite(self.spread, name="floating spread"))
        object.__setattr__(self, "gearing", require_finite(self.gearing, name="floating gearing"))
