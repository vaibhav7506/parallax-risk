"""Immutable, explicit currency-unit inputs for the restricted CCR prototype."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import TradeId
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_currency, require_text, require_tuple


def scalar(value: float, name: str, *, positive: bool = False) -> float:
    result = require_finite(value, name=name)
    if result < 0 or (positive and result == 0):
        raise DomainValidationError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return result


class AssetClass(StrEnum):
    INTEREST_RATE = "interest_rate"
    FX = "fx"
    CREDIT = "credit"
    EQUITY = "equity"
    COMMODITY = "commodity"


@dataclass(frozen=True, slots=True)
class SupervisoryTrade:
    """Linear delta and reporting-currency notional; IR accrual times use ACT/365F."""

    trade_id: TradeId
    asset_class: AssetClass
    currencies: tuple[Currency, ...]
    notional: Money
    delta: float
    maturity: float
    start: float = 0.0
    end: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.trade_id, TradeId) or not isinstance(self.asset_class, AssetClass):
            raise DomainValidationError("CCR trade requires typed identity and asset class")
        require_tuple(self.currencies, Currency, nonempty=True)
        if self.asset_class not in (AssetClass.INTEREST_RATE, AssetClass.FX):
            raise DomainValidationError("Credit/equity/commodity treatments are NOT IMPLEMENTED")
        count = 1 if self.asset_class == AssetClass.INTEREST_RATE else 2
        if len(self.currencies) != count or len(set(self.currencies)) != count:
            raise DomainValidationError(
                "CCR hedging set needs one IR currency or two FX currencies"
            )
        if not isinstance(self.notional, Money) or self.notional.amount < 0:
            raise DomainValidationError("Supervisory notional requires nonnegative Money")
        if require_finite(self.delta, name="linear delta") not in (-1.0, 1.0):
            raise DomainValidationError(
                "Only explicit linear supervisory deltas +/-1 are supported"
            )
        scalar(self.maturity, "remaining maturity", positive=True)
        scalar(self.start, "accrual start")
        scalar(self.end, "accrual end")
        if self.asset_class == AssetClass.INTEREST_RATE:
            if not self.start < self.end <= self.maturity:
                raise DomainValidationError("IR times require 0 <= start < end <= maturity")
        elif self.start != 0 or self.end != 0:
            raise DomainValidationError("FX inputs cannot contain IR duration times")


@dataclass(frozen=True, slots=True)
class SupervisoryParameters:
    """Caller-versioned research assumptions; no jurisdiction or eligibility inference."""

    source: str
    alpha: float = 1.4
    interest_rate_factor: float = 0.005
    fx_factor: float = 0.04
    duration_decay: float = 0.05
    multiplier_floor: float = 0.05
    business_days_per_year: int = 250
    minimum_horizon_business_days: int = 10

    def __post_init__(self) -> None:
        require_text(self.source)
        for name in ("alpha", "interest_rate_factor", "fx_factor", "duration_decay"):
            scalar(getattr(self, name), name, positive=True)
        if not 0 < require_finite(self.multiplier_floor, name="multiplier floor") < 1:
            raise DomainValidationError("Multiplier floor must lie strictly between zero and one")
        if (
            type(self.business_days_per_year) is not int
            or type(self.minimum_horizon_business_days) is not int
            or not 1 <= self.minimum_horizon_business_days <= self.business_days_per_year
        ):
            raise DomainValidationError("Explicit positive business-day convention is required")


@dataclass(frozen=True, slots=True)
class MarginTerms:
    """Explicit regulatory-style inputs, distinct from calendar-day CSA policy/IA."""

    threshold: Money
    minimum_transfer_amount: Money
    net_independent_collateral: Money
    margin_period_business_days: int
    source: str

    def __post_init__(self) -> None:
        require_text(self.source)
        values = (self.threshold, self.minimum_transfer_amount, self.net_independent_collateral)
        if any(not isinstance(v, Money) for v in values) or len({v.currency for v in values}) != 1:
            raise DomainValidationError("Margin inputs require same-currency Money")
        if self.threshold.amount < 0 or self.minimum_transfer_amount.amount < 0:
            raise DomainValidationError("Threshold and MTA must be nonnegative")
        if (
            type(self.margin_period_business_days) is not int
            or self.margin_period_business_days < 10
        ):
            raise DomainValidationError(
                "Prototype bilateral MPOR requires at least 10 business days"
            )


@dataclass(frozen=True, slots=True)
class StandardizedInputs:
    """One enforceable legal unit (or individual trade); C positive means held collateral."""

    scope: str
    value: Money
    collateral: Money
    trades: tuple[SupervisoryTrade, ...]
    margin: MarginTerms | None = None

    def __post_init__(self) -> None:
        require_text(self.scope)
        if not isinstance(self.value, Money) or not isinstance(self.collateral, Money):
            raise DomainValidationError("CCR values require Money")
        require_tuple(self.trades, SupervisoryTrade, nonempty=True)
        if len({t.trade_id for t in self.trades}) != len(self.trades):
            raise DomainValidationError("CCR trade IDs must be unique")
        currencies = {
            self.value.currency,
            self.collateral.currency,
            *(t.notional.currency for t in self.trades),
        }
        if self.margin is not None:
            if not isinstance(self.margin, MarginTerms):
                raise DomainValidationError("Margin terms must be validated")
            currencies.add(self.margin.threshold.currency)
        if len(currencies) != 1:
            raise DomainValidationError("All standardized amounts must share reporting currency")
        object.__setattr__(
            self, "trades", tuple(sorted(self.trades, key=lambda t: str(t.trade_id)))
        )


@dataclass(frozen=True, slots=True)
class ComparisonPolicy:
    currency: Currency
    absolute_tolerance: Money
    relative_tolerance: float
    risk_weight: float
    capital_ratio: float
    source: str
    challenger_alpha: float = 1.4

    def __post_init__(self) -> None:
        require_currency(self.currency)
        require_text(self.source)
        if (
            not isinstance(self.absolute_tolerance, Money)
            or self.absolute_tolerance.currency != self.currency
            or self.absolute_tolerance.amount < 0
        ):
            raise DomainValidationError("Exception tolerance requires nonnegative reporting Money")
        for name in ("relative_tolerance", "risk_weight", "capital_ratio"):
            scalar(getattr(self, name), name)
        if self.capital_ratio > 1:
            raise DomainValidationError("Illustrative capital ratio must lie in [0,1]")
        scalar(self.challenger_alpha, "challenger alpha", positive=True)
