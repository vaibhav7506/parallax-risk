"""Immutable daily market snapshot; no implicit missing-data fallback."""

from dataclasses import dataclass, replace
from datetime import date

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import MarketDataError, MissingMarketDataError
from parallax_risk.common.identifiers import MarketSnapshotId, MarketSnapshotVersion
from parallax_risk.common.math import accumulation_factor
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import (
    positive_accrual,
    require_currency,
    require_token,
    require_tuple,
)
from parallax_risk.domain.market.observations import (
    CreditSpreadObservation,
    FxSpot,
    Quote,
    RateFixing,
    RateObservation,
    VolatilityObservation,
)

type Observation = (
    Quote | RateObservation | FxSpot | VolatilityObservation | CreditSpreadObservation | RateFixing
)


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Explicit currencies and source-labelled data, canonically ordered by quote ID.

    Missing categories may be empty; a requested missing value always raises.
    Observation UTC dates may not exceed the daily valuation date. This daily
    cutoff is not an exchange-specific intraday timestamp policy.
    """

    snapshot_id: MarketSnapshotId
    version: MarketSnapshotVersion
    valuation_date: date
    currencies: tuple[Currency, ...]
    quotes: tuple[Quote, ...] = ()
    rates: tuple[RateObservation, ...] = ()
    fx_spots: tuple[FxSpot, ...] = ()
    volatilities: tuple[VolatilityObservation, ...] = ()
    credit_spreads: tuple[CreditSpreadObservation, ...] = ()
    fixings: tuple[RateFixing, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, MarketSnapshotId) or not isinstance(
            self.version, MarketSnapshotVersion
        ):
            raise MarketDataError("Snapshot identity and version must be explicitly typed")
        require_date(self.valuation_date)
        require_tuple(self.currencies, Currency, nonempty=True)
        if len(set(self.currencies)) != len(self.currencies):
            raise MarketDataError("Snapshot currencies must be unique")
        require_tuple(self.quotes, Quote)
        require_tuple(self.rates, RateObservation)
        require_tuple(self.fx_spots, FxSpot)
        require_tuple(self.volatilities, VolatilityObservation)
        require_tuple(self.credit_spreads, CreditSpreadObservation)
        require_tuple(self.fixings, RateFixing)
        observations: tuple[Observation, ...] = (
            *self.quotes,
            *self.rates,
            *self.fx_spots,
            *self.volatilities,
            *self.credit_spreads,
            *self.fixings,
        )
        if not observations or len({item.quote_id for item in observations}) != len(observations):
            raise MarketDataError("Snapshot requires observations with unique quote IDs")
        for item in observations:
            currencies = (
                (item.base_currency, item.quote_currency)
                if isinstance(item, FxSpot)
                else (item.currency,)
            )
            if any(currency not in self.currencies for currency in currencies):
                raise MarketDataError("Observation currency is absent from snapshot currencies")
            if item.source.observed_at.date() > self.valuation_date:
                raise MarketDataError("Observation lies after the declared daily valuation cutoff")
        for rate in self.rates:
            time = positive_accrual(self.valuation_date, rate.maturity, rate.day_count)
            accumulation_factor(
                rate.rate, time, rate.compounding, periods_per_year=rate.periods_per_year
            )
        if any(item.expiry <= self.valuation_date for item in self.volatilities):
            raise MarketDataError("Volatility expiry must follow valuation date")
        if any(item.maturity <= self.valuation_date for item in self.credit_spreads):
            raise MarketDataError("Credit spread maturity must follow valuation date")
        if any(item.value_date < self.valuation_date for item in self.fx_spots):
            raise MarketDataError("FX spot value date cannot precede valuation date")
        if any(item.fixing_date > self.valuation_date for item in self.fixings):
            raise MarketDataError("Future index fixings cannot be represented as observed fixings")
        pairs = {(item.base_currency, item.quote_currency) for item in self.fx_spots}
        if len(pairs) != len(self.fx_spots) or any((quote, base) in pairs for base, quote in pairs):
            raise MarketDataError("Specify exactly one orientation per FX currency pair")
        keys = {(item.currency, item.index, item.fixing_date) for item in self.fixings}
        if len(keys) != len(self.fixings):
            raise MarketDataError("Duplicate index fixing key")
        rate_keys = {(item.currency, item.index, item.maturity) for item in self.rates}
        if len(rate_keys) != len(self.rates):
            raise MarketDataError("Duplicate rate observation key")
        vol_keys = {
            (item.currency, item.underlying, item.expiry, item.strike, item.convention)
            for item in self.volatilities
        }
        if len(vol_keys) != len(self.volatilities):
            raise MarketDataError("Duplicate volatility observation key")
        credit_keys = {
            (item.currency, item.counterparty_id, item.maturity) for item in self.credit_spreads
        }
        if len(credit_keys) != len(self.credit_spreads):
            raise MarketDataError("Duplicate credit spread observation key")
        object.__setattr__(self, "currencies", tuple(sorted(self.currencies)))
        for name in ("quotes", "rates", "fx_spots", "volatilities", "credit_spreads", "fixings"):
            collection = getattr(self, name)
            object.__setattr__(
                self, name, tuple(sorted(collection, key=lambda item: item.quote_id.value))
            )

    @property
    def snapshot_hash(self) -> str:
        """Content digest includes identity/version, conventions and all provenance."""
        return content_hash(self)

    def fx_spot(self, base: Currency, quote: Currency) -> FxSpot:
        """Retrieve the explicit direct orientation; never synthesize inverse/cross quotes."""
        require_currency(base)
        require_currency(quote)
        for spot in self.fx_spots:
            if spot.base_currency == base and spot.quote_currency == quote:
                return spot
        raise MissingMarketDataError("Requested direct FX spot is absent from snapshot")

    def fixing(self, currency: Currency, index: str, fixing_date: date) -> RateFixing:
        """Retrieve a known fixing exactly by currency/index/date."""
        require_currency(currency)
        require_token(index)
        require_date(fixing_date)
        for fixing in self.fixings:
            if (fixing.currency, fixing.index, fixing.fixing_date) == (
                currency,
                index,
                fixing_date,
            ):
                return fixing
        raise MissingMarketDataError("Required historical index fixing is absent from snapshot")

    def with_fx_rate(
        self, base: Currency, quote: Currency, rate: float, *, version: MarketSnapshotVersion
    ) -> "MarketSnapshot":
        """Create a new explicitly versioned snapshot; the original stays immutable."""
        if version == self.version:
            raise MarketDataError("Updated snapshot must use a different version")
        original = self.fx_spot(base, quote)
        spots = tuple(
            replace(item, rate=rate) if item == original else item for item in self.fx_spots
        )
        return replace(self, version=version, fx_spots=spots)
