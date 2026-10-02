"""Pydantic market ingestion boundary; no HTTP, persistence or unsafe file loading."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.identifiers import (
    CounterpartyId,
    MarketSnapshotId,
    MarketSnapshotVersion,
    QuoteId,
)
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain.market.observations import (
    CreditSpreadObservation,
    FxSpot,
    Quote,
    QuoteUnit,
    RateFixing,
    RateObservation,
    SourceMetadata,
    VolatilityConvention,
    VolatilityObservation,
)
from parallax_risk.domain.market.snapshot import MarketSnapshot


class MarketInput(BaseModel):
    """Frozen, finite, extra-forbidden market-data boundary base."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @field_validator(
        "value", "rate", "strike", "volatility", "spread", mode="before", check_fields=False
    )
    @classmethod
    def strict_numeric(cls, value: object) -> object:
        """Market numeric fields require JSON numbers, never bool or numeric text."""
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("Market values require explicit finite numeric inputs")
        return value

    @field_validator(
        "valuation_date",
        "maturity",
        "value_date",
        "expiry",
        "fixing_date",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def civil_date(cls, value: object) -> object:
        """Require civil date objects or canonical ISO dates, without timestamp inference."""
        if type(value) is date:
            return value
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        raise ValueError("Civil dates require a date or YYYY-MM-DD string")


class SourceInput(MarketInput):
    """Explicit provenance; missing sample status is invalid."""

    name: str
    reference: str
    observed_at: datetime
    is_sample: StrictBool

    @field_validator("observed_at", mode="before")
    @classmethod
    def explicit_timestamp(cls, value: object) -> object:
        """Reject numeric epoch coercion; timezone must be supplied in a timestamp."""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError("Observation time requires an explicitly zoned timestamp")
        return value

    @field_validator("observed_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        """Require a timezone and normalize to UTC."""
        return utc_timestamp(value)

    def to_domain(self) -> SourceMetadata:
        """Map validated boundary fields into an independent immutable source."""
        return SourceMetadata(self.name, self.reference, self.observed_at, self.is_sample)


class QuoteInput(MarketInput):
    """Generic numeric quote with explicit unit and currency context."""

    quote_id: str
    currency: Currency
    value: float
    unit: QuoteUnit
    source: SourceInput

    def to_domain(self) -> Quote:
        """Create a domain quote."""
        return Quote(
            QuoteId(self.quote_id), self.currency, self.value, self.unit, self.source.to_domain()
        )


class RateInput(MarketInput):
    """Annual decimal rate observation, with explicit compounding and day count."""

    quote_id: str
    currency: Currency
    index: str
    maturity: date
    rate: float
    day_count: DayCount
    compounding: Compounding
    source: SourceInput
    periods_per_year: int | None = Field(default=None, strict=True, ge=1)

    def to_domain(self) -> RateObservation:
        """Create a domain rate observation."""
        return RateObservation(
            QuoteId(self.quote_id),
            self.currency,
            self.index,
            self.maturity,
            self.rate,
            self.day_count,
            self.compounding,
            self.source.to_domain(),
            self.periods_per_year,
        )


class FixingInput(MarketInput):
    """Observed historical rate; maturity and projection are deliberately separate."""

    quote_id: str
    currency: Currency
    index: str
    fixing_date: date
    rate: float
    source: SourceInput

    def to_domain(self) -> RateFixing:
        """Create a domain fixing."""
        return RateFixing(
            QuoteId(self.quote_id),
            self.currency,
            self.index,
            self.fixing_date,
            self.rate,
            self.source.to_domain(),
        )


class FxSpotInput(MarketInput):
    """Direct QUOTE/BASE spot for a declared settlement date."""

    quote_id: str
    base_currency: Currency
    quote_currency: Currency
    value_date: date
    rate: float
    source: SourceInput

    def to_domain(self) -> FxSpot:
        """Create a domain FX quote."""
        return FxSpot(
            QuoteId(self.quote_id),
            self.base_currency,
            self.quote_currency,
            self.value_date,
            self.rate,
            self.source.to_domain(),
        )


class VolatilityInput(MarketInput):
    """Raw volatility observation; no fitted surface/model is created."""

    quote_id: str
    currency: Currency
    underlying: str
    expiry: date
    strike: float
    volatility: float
    convention: VolatilityConvention
    source: SourceInput

    def to_domain(self) -> VolatilityObservation:
        """Create a domain volatility observation."""
        return VolatilityObservation(
            QuoteId(self.quote_id),
            self.currency,
            self.underlying,
            self.expiry,
            self.strike,
            self.volatility,
            self.convention,
            self.source.to_domain(),
        )


class CreditSpreadInput(MarketInput):
    """Observed decimal annual credit spread with explicit entity and currency."""

    quote_id: str
    currency: Currency
    counterparty_id: str
    maturity: date
    spread: float
    source: SourceInput

    def to_domain(self) -> CreditSpreadObservation:
        """Create a domain credit observation without inferring hazard rates."""
        return CreditSpreadObservation(
            QuoteId(self.quote_id),
            self.currency,
            CounterpartyId(self.counterparty_id),
            self.maturity,
            self.spread,
            self.source.to_domain(),
        )


class MarketSnapshotInput(MarketInput):
    """Validate complete daily snapshots from JSON or typed boundary data."""

    snapshot_id: str
    version: str
    valuation_date: date
    currencies: tuple[Currency, ...]
    quotes: tuple[QuoteInput, ...] = ()
    rates: tuple[RateInput, ...] = ()
    fx_spots: tuple[FxSpotInput, ...] = ()
    volatilities: tuple[VolatilityInput, ...] = ()
    credit_spreads: tuple[CreditSpreadInput, ...] = ()
    fixings: tuple[FixingInput, ...] = ()

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply the same consistency rules as direct domain construction."""
        self.to_domain()
        return self

    def to_domain(self) -> MarketSnapshot:
        """Create an immutable snapshot without retaining mutable boundary inputs."""
        return MarketSnapshot(
            MarketSnapshotId(self.snapshot_id),
            MarketSnapshotVersion(self.version),
            self.valuation_date,
            self.currencies,
            tuple(item.to_domain() for item in self.quotes),
            tuple(item.to_domain() for item in self.rates),
            tuple(item.to_domain() for item in self.fx_spots),
            tuple(item.to_domain() for item in self.volatilities),
            tuple(item.to_domain() for item in self.credit_spreads),
            tuple(item.to_domain() for item in self.fixings),
        )
