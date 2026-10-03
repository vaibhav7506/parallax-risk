import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

import pytest
from pydantic import ValidationError

from parallax_risk.application.market_data import MarketSnapshotInput
from parallax_risk.common.canonical import canonical_value, content_hash
from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.errors import (
    DomainValidationError,
    MarketDataError,
    MissingMarketDataError,
    NumericalError,
)
from parallax_risk.common.identifiers import CounterpartyId, MarketSnapshotVersion, QuoteId, TradeId
from parallax_risk.domain.market.observations import (
    CreditSpreadObservation,
    Quote,
    QuoteUnit,
    RateObservation,
    SourceMetadata,
    VolatilityConvention,
    VolatilityObservation,
)
from tests.fixtures.deterministic import INDEX, SOURCE, VALUATION, YEAR_ONE, market


def complete_snapshot():
    base = market()
    return replace(
        base,
        quotes=(Quote(QuoteId("price"), Currency.USD, 100, QuoteUnit.CURRENCY_UNITS, SOURCE),),
        rates=(
            RateObservation(
                QuoteId("rate"),
                Currency.USD,
                INDEX,
                YEAR_ONE,
                0.05,
                DayCount.ACT_365_FIXED,
                Compounding.CONTINUOUS,
                SOURCE,
            ),
        ),
        volatilities=(
            VolatilityObservation(
                QuoteId("vol"),
                Currency.USD,
                "SYNTH",
                YEAR_ONE,
                100,
                0.2,
                VolatilityConvention.LOGNORMAL,
                SOURCE,
            ),
        ),
        credit_spreads=(
            CreditSpreadObservation(
                QuoteId("credit"), Currency.USD, CounterpartyId("cp"), YEAR_ONE, 0.01, SOURCE
            ),
        ),
    )


def test_snapshot_frozen_canonical_and_versioned():
    snapshot = complete_snapshot()
    reordered = replace(snapshot, currencies=snapshot.currencies[::-1])
    assert reordered.snapshot_hash == snapshot.snapshot_hash
    assert len(snapshot.snapshot_hash) == 64
    with pytest.raises(FrozenInstanceError):
        snapshot.version = MarketSnapshotVersion("2")
    with pytest.raises(FrozenInstanceError):
        snapshot.rates[0].rate = 3
    changed = snapshot.with_fx_rate(
        Currency.EUR, Currency.USD, 1.2, version=MarketSnapshotVersion("2")
    )
    assert snapshot.fx_spot(Currency.EUR, Currency.USD).rate == 1.1
    assert changed.snapshot_hash != snapshot.snapshot_hash
    assert changed.version == MarketSnapshotVersion("2")
    with pytest.raises(MarketDataError, match="different version"):
        snapshot.with_fx_rate(Currency.EUR, Currency.USD, 1.2, version=snapshot.version)
    assert (
        replace(
            snapshot,
            rates=(replace(snapshot.rates[0], source=replace(SOURCE, reference="different")),),
        ).snapshot_hash
        != snapshot.snapshot_hash
    )
    assert (
        replace(snapshot, rates=(replace(snapshot.rates[0], rate=0.06),)).snapshot_hash
        != snapshot.snapshot_hash
    )
    assert snapshot.fixing(Currency.USD, INDEX, VALUATION).rate > 0


def test_snapshot_quote_order_does_not_change_hash():
    quote = Quote(QuoteId("a"), Currency.USD, 1, QuoteUnit.DIMENSIONLESS, SOURCE)
    another = replace(quote, quote_id=QuoteId("b"), value=2)
    assert (
        replace(market(), quotes=(quote, another)).snapshot_hash
        == replace(market(), quotes=(another, quote)).snapshot_hash
    )


def test_missing_quotes_and_fixings_are_explicit():
    snapshot = market()
    with pytest.raises(MissingMarketDataError):
        snapshot.fx_spot(Currency.USD, Currency.EUR)
    with pytest.raises(MissingMarketDataError):
        snapshot.fixing(Currency.USD, "MISSING", VALUATION)
    with pytest.raises(MissingMarketDataError):
        snapshot.with_fx_rate(Currency.USD, Currency.EUR, 1, version=MarketSnapshotVersion("2"))


@pytest.mark.parametrize(
    "case",
    [
        "id",
        "version",
        "empty",
        "mutable",
        "currency_duplicate",
        "currency_missing",
        "quote_duplicate",
        "future_source",
        "past_rate",
        "expired_vol",
        "expired_credit",
        "past_spot",
        "future_fixing",
        "pair_duplicate",
        "pair_inverse",
        "fixing_duplicate",
        "rate_duplicate",
        "vol_duplicate",
        "credit_duplicate",
    ],
)
def test_snapshot_rejects_malformed_and_ambiguous_data(case):
    snapshot = complete_snapshot()
    updates = {
        "id": {"snapshot_id": "x"},
        "version": {"version": "1"},
        "empty": {
            "quotes": (),
            "rates": (),
            "fx_spots": (),
            "volatilities": (),
            "credit_spreads": (),
            "fixings": (),
        },
        "mutable": {"currencies": [Currency.USD, Currency.EUR]},
        "currency_duplicate": {"currencies": (Currency.USD, Currency.USD)},
        "currency_missing": {"currencies": (Currency.EUR,)},
        "quote_duplicate": {
            "quotes": (replace(snapshot.quotes[0], quote_id=snapshot.rates[0].quote_id),)
        },
        "future_source": {
            "quotes": (
                replace(
                    snapshot.quotes[0],
                    source=replace(SOURCE, observed_at=datetime(2025, 1, 2, tzinfo=UTC)),
                ),
            )
        },
        "past_rate": {"rates": (replace(snapshot.rates[0], maturity=VALUATION),)},
        "expired_vol": {"volatilities": (replace(snapshot.volatilities[0], expiry=VALUATION),)},
        "expired_credit": {
            "credit_spreads": (replace(snapshot.credit_spreads[0], maturity=VALUATION),)
        },
        "past_spot": {"fx_spots": (replace(snapshot.fx_spots[0], value_date=date(2024, 12, 31)),)},
        "future_fixing": {"fixings": (replace(snapshot.fixings[0], fixing_date=YEAR_ONE),)},
        "pair_duplicate": {
            "fx_spots": (
                *snapshot.fx_spots,
                replace(snapshot.fx_spots[0], quote_id=QuoteId("other")),
            )
        },
        "pair_inverse": {
            "fx_spots": (
                *snapshot.fx_spots,
                replace(
                    snapshot.fx_spots[0],
                    quote_id=QuoteId("other"),
                    base_currency=Currency.USD,
                    quote_currency=Currency.EUR,
                ),
            )
        },
        "fixing_duplicate": {
            "fixings": (*snapshot.fixings, replace(snapshot.fixings[0], quote_id=QuoteId("other")))
        },
        "rate_duplicate": {
            "rates": (*snapshot.rates, replace(snapshot.rates[0], quote_id=QuoteId("other")))
        },
        "vol_duplicate": {
            "volatilities": (
                *snapshot.volatilities,
                replace(snapshot.volatilities[0], quote_id=QuoteId("other")),
            )
        },
        "credit_duplicate": {
            "credit_spreads": (
                *snapshot.credit_spreads,
                replace(snapshot.credit_spreads[0], quote_id=QuoteId("other")),
            )
        },
    }
    with pytest.raises(DomainValidationError):
        replace(snapshot, **updates[case])


@pytest.mark.parametrize(
    "factory",
    [
        lambda: replace(SOURCE, name=""),
        lambda: replace(SOURCE, reference=" "),
        lambda: replace(SOURCE, is_sample=1),
        lambda: replace(complete_snapshot().quotes[0], value=float("nan")),
        lambda: replace(complete_snapshot().quotes[0], quote_id="x"),
        lambda: replace(complete_snapshot().quotes[0], source="source"),
        lambda: replace(complete_snapshot().quotes[0], currency="USD"),
        lambda: replace(complete_snapshot().quotes[0], unit="dimensionless"),
        lambda: replace(complete_snapshot().rates[0], day_count="ACT/365F"),
        lambda: replace(market().fx_spots[0], rate=0),
        lambda: replace(market().fx_spots[0], quote_currency=Currency.EUR),
        lambda: replace(complete_snapshot().volatilities[0], volatility=-1),
        lambda: replace(complete_snapshot().volatilities[0], convention="lognormal"),
        lambda: replace(complete_snapshot().volatilities[0], strike=0),
        lambda: replace(complete_snapshot().credit_spreads[0], counterparty_id="cp"),
        lambda: replace(complete_snapshot().credit_spreads[0], spread=-1),
    ],
)
def test_observations_reject_invalid_values(factory):
    with pytest.raises((DomainValidationError, NumericalError)):
        factory()


def boundary_payload():
    source = {
        "name": "synthetic",
        "reference": "test",
        "observed_at": "2025-01-01T00:00:00Z",
        "is_sample": True,
    }
    return {
        "snapshot_id": "sample",
        "version": "1",
        "valuation_date": "2025-01-01",
        "currencies": ["USD", "EUR"],
        "quotes": [
            {
                "quote_id": "price",
                "currency": "USD",
                "value": 100,
                "unit": "currency_units",
                "source": source,
            }
        ],
        "rates": [
            {
                "quote_id": "rate",
                "currency": "USD",
                "index": INDEX,
                "maturity": "2026-01-01",
                "rate": 0.05,
                "day_count": "ACT/365F",
                "compounding": "continuous",
                "source": source,
            }
        ],
        "fx_spots": [
            {
                "quote_id": "fx",
                "base_currency": "EUR",
                "quote_currency": "USD",
                "value_date": "2025-01-01",
                "rate": 1.1,
                "source": source,
            }
        ],
        "volatilities": [
            {
                "quote_id": "vol",
                "currency": "USD",
                "underlying": "SYNTH",
                "expiry": "2026-01-01",
                "strike": 100,
                "volatility": 0.2,
                "convention": "lognormal",
                "source": source,
            }
        ],
        "credit_spreads": [
            {
                "quote_id": "credit",
                "currency": "USD",
                "counterparty_id": "cp",
                "maturity": "2026-01-01",
                "spread": 0.01,
                "source": source,
            }
        ],
        "fixings": [
            {
                "quote_id": "fix",
                "currency": "USD",
                "index": INDEX,
                "fixing_date": "2025-01-01",
                "rate": 0.05,
                "source": source,
            }
        ],
    }


def test_pydantic_json_ingestion_and_mutation_isolation():
    payload = boundary_payload()
    boundary = MarketSnapshotInput.model_validate(payload)
    result = boundary.to_domain()
    replay = MarketSnapshotInput.model_validate_json(json.dumps(payload)).to_domain()
    assert result.snapshot_hash == replay.snapshot_hash
    payload["quotes"][0]["value"] = 999
    assert result.quotes[0].value == 100
    with pytest.raises(ValidationError):
        boundary.version = "2"
    assert boundary.rates[0].periods_per_year is None


@pytest.mark.parametrize("value", [1735689600, 1735689600.0, True, "20250101", "2025-W01-3"])
def test_ingestion_does_not_infer_civil_dates_from_epochs_or_noncanonical_text(value):
    payload = boundary_payload()
    payload["valuation_date"] = value
    with pytest.raises(ValidationError):
        MarketSnapshotInput.model_validate(payload)


@pytest.mark.parametrize("value", [1735689600, 1735689600.0, True, "1735689600"])
def test_ingestion_does_not_infer_timezone_from_epoch_numbers(value):
    payload = boundary_payload()
    payload["quotes"][0]["source"]["observed_at"] = value
    with pytest.raises(ValidationError):
        MarketSnapshotInput.model_validate(payload)


def test_ingestion_accepts_explicit_civil_date_objects():
    payload = boundary_payload()
    payload["valuation_date"] = VALUATION
    payload["quotes"][0]["source"]["observed_at"] = SOURCE.observed_at
    assert MarketSnapshotInput.model_validate(payload).valuation_date == VALUATION


@pytest.mark.parametrize(
    "case", ["missing", "extra", "bool", "text", "nan", "naive", "sample", "date_time", "duplicate"]
)
def test_pydantic_rejects_malformed_boundary_data(case):
    payload = boundary_payload()
    if case == "missing":
        del payload["currencies"]
    elif case == "extra":
        payload["arbitrary_python"] = "run()"
    elif case in {"bool", "text", "nan"}:
        payload["rates"][0]["rate"] = {"bool": True, "text": "0.05", "nan": float("nan")}[case]
    elif case == "naive":
        payload["quotes"][0]["source"]["observed_at"] = "2025-01-01T00:00:00"
    elif case == "sample":
        del payload["quotes"][0]["source"]["is_sample"]
    elif case == "date_time":
        payload["valuation_date"] = datetime(2025, 1, 1)
    else:
        payload["fx_spots"][0]["quote_id"] = "price"
    with pytest.raises(ValidationError):
        MarketSnapshotInput.model_validate(payload)


def test_canonical_fingerprint_types_and_rejections():
    class Kind(Enum):
        VALUE = "value"

    assert canonical_value(Kind.VALUE) == "value"
    assert canonical_value(Decimal("1.00")) == "1.00"
    assert canonical_value(VALUATION) == "2025-01-01"
    assert canonical_value(SOURCE.observed_at) == "2025-01-01T00:00:00+00:00"
    assert content_hash({"a": 1, "b": True}) == content_hash({"b": True, "a": 1})
    assert content_hash(QuoteId("same")) != content_hash(TradeId("same"))
    assert canonical_value(None) is None
    for value in (Decimal("NaN"), {1: "bad"}, object(), SourceMetadata, [1]):
        with pytest.raises(DomainValidationError):
            canonical_value(value)
    with pytest.raises(NumericalError):
        canonical_value(float("inf"))
