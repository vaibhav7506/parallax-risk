"""Explicit research CSA conventions; no regulatory or legal eligibility inference."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CsaId
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_currency, require_tuple


class CollateralDirection(StrEnum):
    """Bank perspective: collect only, post only, or exchange in both directions."""

    RECEIVE_ONLY = "receive_only"
    POST_ONLY = "post_only"
    TWO_WAY = "two_way"


@dataclass(frozen=True, slots=True)
class EligibleCollateral:
    """Cash currency with caller-declared total valuation haircut in [0, 1)."""

    currency: Currency
    haircut: Decimal

    def __post_init__(self) -> None:
        require_currency(self.currency)
        if (
            not isinstance(self.haircut, Decimal)
            or not self.haircut.is_finite()
            or not 0 <= self.haircut < 1
        ):
            raise DomainValidationError("Haircut must be finite Decimal in [0, 1)")

    @property
    def valuation_factor(self) -> Decimal:
        """Compute 1-h under the exact Money precision contract."""
        return (Money(Decimal(1), self.currency) - Money(self.haircut, self.currency)).amount


def calendar_offset(start: date, days: int) -> date:
    """Explicit calendar-day policy; no business-day/calendar inference."""
    require_date(start)
    if type(days) is not int or days < 0:
        raise DomainValidationError("Calendar-day offset must be nonnegative integer")
    try:
        return start + timedelta(days=days)
    except (OverflowError, ValueError):
        raise DomainValidationError("Calendar offset exceeds supported date range") from None


@dataclass(frozen=True, slots=True)
class Csa:
    """Signed title-transfer IA plus VM, with symmetric strict-greater MTA policy.

    IA is a signed, reusable independent amount in agreement currency. It is not
    segregated regulatory initial margin. Zero IA explicitly disables that buffer.
    All day fields use calendar days, anchored to the first margin date.
    """

    csa_id: CsaId
    currency: Currency
    receive_threshold: Money
    post_threshold: Money
    minimum_transfer_amount: Money
    independent_amount: Money
    eligible_collateral: tuple[EligibleCollateral, ...]
    direction: CollateralDirection
    first_margin_date: date
    frequency_days: int
    settlement_lag_days: int
    margin_period_of_risk_days: int

    def __post_init__(self) -> None:
        if not isinstance(self.csa_id, CsaId):
            raise DomainValidationError("CSA identity must be typed")
        require_currency(self.currency)
        require_date(self.first_margin_date)
        if not isinstance(self.direction, CollateralDirection):
            raise DomainValidationError("Collateral direction must be explicit")
        for value in (
            self.receive_threshold,
            self.post_threshold,
            self.minimum_transfer_amount,
            self.independent_amount,
        ):
            if not isinstance(value, Money) or value.currency != self.currency:
                raise DomainValidationError("CSA amounts require agreement-currency Money")
        if any(
            v.amount < 0
            for v in (self.receive_threshold, self.post_threshold, self.minimum_transfer_amount)
        ):
            raise DomainValidationError("CSA thresholds and MTA must be nonnegative")
        require_tuple(self.eligible_collateral, EligibleCollateral, nonempty=True)
        if len({e.currency for e in self.eligible_collateral}) != len(self.eligible_collateral):
            raise DomainValidationError("Eligible collateral currencies must be unique")
        self.validate_direction(self.independent_amount)
        for name in ("frequency_days", "settlement_lag_days", "margin_period_of_risk_days"):
            count = getattr(self, name)
            if type(count) is not int or count < (1 if name == "frequency_days" else 0):
                raise DomainValidationError("CSA day counts must be valid integers")
            calendar_offset(self.first_margin_date, count)
        object.__setattr__(
            self,
            "eligible_collateral",
            tuple(sorted(self.eligible_collateral, key=lambda e: e.currency)),
        )

    def eligible(self, currency: Currency) -> EligibleCollateral:
        """Exact eligibility lookup; reject missing currencies."""
        require_currency(currency)
        for item in self.eligible_collateral:
            if item.currency == currency:
                return item
        raise DomainValidationError("Currency is not eligible under this CSA")

    def validate_direction(self, balance: Money) -> None:
        """One-way accounts cannot finish with collateral held by the wrong party."""
        if (self.direction == CollateralDirection.RECEIVE_ONLY and balance.amount < 0) or (
            self.direction == CollateralDirection.POST_ONLY and balance.amount > 0
        ):
            raise DomainValidationError("Collateral balance violates one-way agreement")

    def margin_date(self, as_of: date) -> bool:
        """Fixed schedule; off-schedule reviews do not issue calls."""
        require_date(as_of)
        elapsed = (as_of - self.first_margin_date).days
        return elapsed >= 0 and elapsed % self.frequency_days == 0

    def target(self, value: Money) -> tuple[Money, Money]:
        """Return VM target and total target (VM plus signed independent amount)."""
        if not isinstance(value, Money) or value.currency != self.currency:
            raise DomainValidationError("CSA valuation must use agreement currency")
        zero = Money(Decimal(0), self.currency)
        receive = value - self.receive_threshold
        post = -value - self.post_threshold
        vm = (
            (receive if receive.amount > 0 else zero)
            if (self.direction != CollateralDirection.POST_ONLY)
            else zero
        )
        if self.direction != CollateralDirection.RECEIVE_ONLY and post.amount > 0:
            vm = vm - post
        return vm, vm + self.independent_amount
