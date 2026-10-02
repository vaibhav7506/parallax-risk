"""Hand-specified synthetic conventions; nothing here is represented as observed market data."""

import math
from datetime import UTC, date, datetime
from decimal import Decimal

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import (
    CurveId,
    MarketSnapshotId,
    MarketSnapshotVersion,
    QuoteId,
)
from parallax_risk.common.money import Money
from parallax_risk.domain.instruments.cashflows import AccrualPeriod
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import CurveSet, DiscountCurve, ForwardCurve
from parallax_risk.domain.market.observations import FxSpot, RateFixing, SourceMetadata
from parallax_risk.domain.market.snapshot import MarketSnapshot
from parallax_risk.domain.pricing.engine import PricingContext

VALUATION = date(2025, 1, 1)
YEAR_ONE = date(2026, 1, 1)
YEAR_TWO = date(2027, 1, 1)
SOURCE = SourceMetadata(
    "synthetic", "hand-derived Phase 2 fixture", datetime(2025, 1, 1, tzinfo=UTC), True
)
PERIODS = (
    AccrualPeriod(VALUATION, YEAR_ONE, YEAR_ONE),
    AccrualPeriod(YEAR_ONE, YEAR_TWO, YEAR_TWO),
)
INDEX = "USD-SYNTH-1Y"


def money(amount="100", currency=Currency.USD):
    return Money(Decimal(str(amount)), currency)


def flat_curve(
    currency=Currency.USD, rate=0.05, *, curve_id=None, extrapolation=ExtrapolationPolicy.ERROR
):
    return DiscountCurve(
        CurveId(curve_id or f"{currency}-discount"),
        currency,
        VALUATION,
        DayCount.ACT_365_FIXED,
        (0.0, 1.0, 2.0),
        (1.0, math.exp(-rate), math.exp(-2 * rate)),
        InterpolationKind.LOG_LINEAR,
        extrapolation,
    )


def market(*, fixing_rate=None, value_date=VALUATION):
    fixing_rate = math.expm1(0.05) if fixing_rate is None else fixing_rate
    return MarketSnapshot(
        MarketSnapshotId("synthetic-test"),
        MarketSnapshotVersion("1"),
        VALUATION,
        (Currency.USD, Currency.EUR),
        fx_spots=(FxSpot(QuoteId("EUR-USD"), Currency.EUR, Currency.USD, value_date, 1.1, SOURCE),),
        fixings=(
            RateFixing(QuoteId("USD-fixing"), Currency.USD, INDEX, VALUATION, fixing_rate, SOURCE),
        ),
    )


def context(*, discount_rate=0.05, projection_rate=None, snapshot=None, include_today=False):
    discount = flat_curve(rate=discount_rate)
    projection = (
        discount
        if projection_rate is None
        else flat_curve(rate=projection_rate, curve_id="USD-projection")
    )
    curves = CurveSet(
        (discount, flat_curve(Currency.EUR, 0.03)), (ForwardCurve(INDEX, projection),)
    )
    return PricingContext(market() if snapshot is None else snapshot, curves, include_today)
