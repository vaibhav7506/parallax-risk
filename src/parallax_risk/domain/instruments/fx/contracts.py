"""Deliverable FX forward, quoted in quote currency per base unit."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import PricingError
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_currency


class FxDirection(StrEnum):
    """Buy base: receive base/pay quote; sell base reverses both payments."""

    BUY_BASE = "buy_base"
    SELL_BASE = "sell_base"


@dataclass(frozen=True, slots=True)
class FxForward:
    """Exchange base notional N for N*K quote units on maturity; NPV is in QUOTE."""

    base_notional: Money
    quote_currency: Currency
    strike: Decimal
    maturity: date
    direction: FxDirection

    def __post_init__(self) -> None:
        if not isinstance(self.base_notional, Money) or self.base_notional.amount < 0:
            raise PricingError("FX base notional must be nonnegative Money")
        require_currency(self.quote_currency)
        require_date(self.maturity)
        if self.base_notional.currency == self.quote_currency:
            raise PricingError("FX forward currencies must differ")
        if not isinstance(self.strike, Decimal) or not self.strike.is_finite() or self.strike <= 0:
            raise PricingError("FX strike must be a strictly positive finite Decimal")
        if not isinstance(self.direction, FxDirection):
            raise PricingError("FX direction must be explicit")
