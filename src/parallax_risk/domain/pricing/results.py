"""Immutable deterministic pricing outputs with cash-flow and input evidence."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import PricingError
from parallax_risk.common.identifiers import CurveId, ModelVersion
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_text, require_tuple


class RateOrigin(StrEnum):
    """Calculation origin for each future payment."""

    KNOWN_PAYMENT = "known_payment"
    FIXED_COUPON = "fixed_coupon"
    HISTORICAL_FIXING = "historical_fixing"
    PROJECTED_FIXING = "projected_fixing"
    REDEMPTION = "redemption"
    FX_PAYMENT = "fx_payment"


@dataclass(frozen=True, slots=True)
class CashFlowPresentValue:
    """Signed original currency amount and discounted value in the result currency."""

    payment_date: date
    amount: Money
    discount_factor: float
    conversion_rate: float
    present_value: Money
    discount_curve_id: CurveId
    rate_origin: RateOrigin
    coupon_rate: float | None = None

    def __post_init__(self) -> None:
        require_date(self.payment_date)
        if not isinstance(self.amount, Money) or not isinstance(self.present_value, Money):
            raise PricingError("Cash-flow evidence requires typed Money")
        if (
            require_finite(self.discount_factor, name="cash-flow discount") <= 0
            or require_finite(self.conversion_rate, name="cash-flow FX conversion") <= 0
        ):
            raise PricingError("Cash-flow discount and conversion must be positive")
        if not isinstance(self.discount_curve_id, CurveId) or not isinstance(
            self.rate_origin, RateOrigin
        ):
            raise PricingError("Cash-flow curve identity and origin must be typed")
        if self.coupon_rate is not None:
            require_finite(self.coupon_rate, name="cash-flow coupon rate")


@dataclass(frozen=True, slots=True)
class PricingResult:
    """NPV with explicit currency/date/model assumptions and complete deterministic inputs."""

    npv: Money
    valuation_date: date
    model_name: str
    model_version: ModelVersion
    assumptions: tuple[str, ...]
    cashflows: tuple[CashFlowPresentValue, ...]
    market_snapshot_hash: str
    curve_set_hash: str
    instrument_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.npv, Money) or not isinstance(self.model_version, ModelVersion):
            raise PricingError("Pricing result requires Money and a model version")
        require_date(self.valuation_date)
        require_text(self.model_name)
        require_tuple(self.assumptions, str, nonempty=True)
        for assumption in self.assumptions:
            require_text(assumption)
        require_tuple(self.cashflows, CashFlowPresentValue)
        if any(item.present_value.currency != self.npv.currency for item in self.cashflows):
            raise PricingError("All cash-flow present values must use the result currency")
        for value in (self.market_snapshot_hash, self.curve_set_hash, self.instrument_hash):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise PricingError("Pricing input fingerprints must be SHA-256 digests")

    @property
    def currency(self) -> Currency:
        """Reporting currency, derived from NPV rather than independently duplicated."""
        return self.npv.currency
