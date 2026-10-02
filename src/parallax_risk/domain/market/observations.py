"""Observed market values with explicit units, conventions and provenance."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.errors import MarketDataError
from parallax_risk.common.identifiers import CounterpartyId, QuoteId
from parallax_risk.common.math import accumulation_factor, require_finite
from parallax_risk.common.time import require_date, utc_timestamp
from parallax_risk.domain._validation import require_currency, require_text, require_token


class QuoteUnit(StrEnum):
    """Generic quote units; annual rates/spreads are decimal, never basis points."""

    CURRENCY_UNITS = "currency_units"
    DECIMAL_ANNUAL_RATE = "decimal_annual_rate"
    DIMENSIONLESS = "dimensionless"


class VolatilityConvention(StrEnum):
    """Lognormal: dimensionless/sqrt(year); normal: currency units/sqrt(year)."""

    LOGNORMAL = "lognormal"
    NORMAL = "normal"


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """External source identity and aware observation instant; sample status is explicit."""

    name: str
    reference: str
    observed_at: datetime
    is_sample: bool

    def __post_init__(self) -> None:
        require_text(self.name)
        require_text(self.reference)
        object.__setattr__(self, "observed_at", utc_timestamp(self.observed_at))
        if type(self.is_sample) is not bool:
            raise MarketDataError("Source sample status must be explicit boolean")


def _observation(
    quote_id: QuoteId, currency: Currency, source: SourceMetadata, value: float
) -> float:
    if not isinstance(quote_id, QuoteId) or not isinstance(source, SourceMetadata):
        raise MarketDataError("Typed quote ID and source metadata are required")
    require_currency(currency)
    return require_finite(value, name="observation")


@dataclass(frozen=True, slots=True)
class Quote:
    """Generic observation with declared currency context and unit."""

    quote_id: QuoteId
    currency: Currency
    value: float
    unit: QuoteUnit
    source: SourceMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _observation(self.quote_id, self.currency, self.source, self.value)
        )
        if not isinstance(self.unit, QuoteUnit):
            raise MarketDataError("Generic quote unit must be declared")


@dataclass(frozen=True, slots=True)
class RateObservation:
    """An annual rate quote, labelled by index and explicit rate/time conventions."""

    quote_id: QuoteId
    currency: Currency
    index: str
    maturity: date
    rate: float
    day_count: DayCount
    compounding: Compounding
    source: SourceMetadata
    periods_per_year: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rate", _observation(self.quote_id, self.currency, self.source, self.rate)
        )
        require_token(self.index)
        require_date(self.maturity)
        if not isinstance(self.day_count, DayCount):
            raise MarketDataError("Rate day count is required")
        accumulation_factor(self.rate, 0, self.compounding, periods_per_year=self.periods_per_year)


@dataclass(frozen=True, slots=True)
class RateFixing:
    """A known index fixing, in decimal annual rate units; never a forecast."""

    quote_id: QuoteId
    currency: Currency
    index: str
    fixing_date: date
    rate: float
    source: SourceMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rate", _observation(self.quote_id, self.currency, self.source, self.rate)
        )
        require_token(self.index)
        require_date(self.fixing_date)


@dataclass(frozen=True, slots=True)
class FxSpot:
    """QUOTE currency units per one BASE unit, delivered on explicit value date."""

    quote_id: QuoteId
    base_currency: Currency
    quote_currency: Currency
    value_date: date
    rate: float
    source: SourceMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rate", _observation(self.quote_id, self.base_currency, self.source, self.rate)
        )
        require_currency(self.quote_currency)
        require_date(self.value_date)
        if self.base_currency == self.quote_currency or self.rate <= 0:
            raise MarketDataError("FX requires different currencies and a strictly positive quote")


@dataclass(frozen=True, slots=True)
class VolatilityObservation:
    """Raw observed volatility; no surface or option-pricing model is inferred."""

    quote_id: QuoteId
    currency: Currency
    underlying: str
    expiry: date
    strike: float
    volatility: float
    convention: VolatilityConvention
    source: SourceMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "volatility",
            _observation(self.quote_id, self.currency, self.source, self.volatility),
        )
        object.__setattr__(self, "strike", require_finite(self.strike, name="volatility strike"))
        require_token(self.underlying)
        require_date(self.expiry)
        if not isinstance(self.convention, VolatilityConvention) or self.volatility < 0:
            raise MarketDataError("Volatility must be nonnegative with explicit convention")
        if self.convention == VolatilityConvention.LOGNORMAL and self.strike <= 0:
            raise MarketDataError("Lognormal volatility observations require positive strike")


@dataclass(frozen=True, slots=True)
class CreditSpreadObservation:
    """Nonnegative decimal annual credit spread; no hazard or recovery mapping yet."""

    quote_id: QuoteId
    currency: Currency
    counterparty_id: CounterpartyId
    maturity: date
    spread: float
    source: SourceMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "spread", _observation(self.quote_id, self.currency, self.source, self.spread)
        )
        require_date(self.maturity)
        if not isinstance(self.counterparty_id, CounterpartyId) or self.spread < 0:
            raise MarketDataError(
                "Credit spread requires typed counterparty and nonnegative spread"
            )
