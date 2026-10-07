"""Replay an explicitly synthetic Phase 5 portfolio through the production service."""

import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from parallax_risk.application.context import RunContext
from parallax_risk.application.market_data import MarketSnapshotInput
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.canonical import canonical_value
from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import (
    CollateralAccountId,
    CollateralMovementId,
    CounterpartyId,
    CsaId,
    CurveId,
    NettingSetId,
    PortfolioId,
    PortfolioVersion,
    RiskRunId,
    TradeId,
)
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.instruments.cashflows import CashFlow
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import CurveSet, ZeroCurve
from parallax_risk.domain.portfolio.collateral import CollateralAccount, CollateralMovement
from parallax_risk.domain.portfolio.contracts import (
    Counterparty,
    NettingSet,
    PortfolioSnapshot,
    Trade,
)
from parallax_risk.domain.portfolio.csa import CollateralDirection, Csa, EligibleCollateral
from parallax_risk.domain.pricing.engine import DiscountingEngine, PricingContext


def example() -> dict[str, object]:
    """Full synthetic inputs and results; safe logs go to stderr, repeatable JSON to stdout."""
    root = Path(__file__).resolve().parents[1]
    snapshot = MarketSnapshotInput.model_validate_json(
        (root / "data/sample/phase2_market.json").read_text(encoding="utf-8")
    ).to_domain()
    curves = []
    for currency in snapshot.currencies:
        rates = sorted(
            (r for r in snapshot.rates if r.currency == currency), key=lambda r: r.maturity
        )
        first = rates[0]
        curves.append(
            ZeroCurve(
                CurveId(f"{currency}-synthetic-phase5"),
                currency,
                snapshot.valuation_date,
                first.day_count,
                (
                    0.0,
                    *(
                        year_fraction(snapshot.valuation_date, r.maturity, first.day_count)
                        for r in rates
                    ),
                ),
                (first.rate, *(r.rate for r in rates)),
                first.compounding,
                ExtrapolationPolicy.ERROR,
                first.periods_per_year,
            ).to_discount_curve(
                interpolation=InterpolationKind.LOG_LINEAR, extrapolation=ExtrapolationPolicy.ERROR
            )
        )
    market = PricingContext(snapshot, CurveSet(tuple(curves)))
    today = snapshot.valuation_date

    def usd(amount: int) -> Money:
        return Money(Decimal(amount), Currency.USD)

    agreement = Csa(
        CsaId("synthetic-csa"),
        Currency.USD,
        usd(10),
        usd(20),
        usd(5),
        usd(0),
        (
            EligibleCollateral(Currency.USD, Decimal(0)),
            EligibleCollateral(Currency.EUR, Decimal("0.2")),
        ),
        CollateralDirection.TWO_WAY,
        today,
        1,
        2,
        10,
    )
    trades = tuple(
        Trade(TradeId(name), CashFlow(date(2026, 1, 1), usd(amount)), Decimal(1), today, today)
        for name, amount in (("receive", 100), ("pay", -80))
    )
    scope = NettingSet(
        NettingSetId("synthetic-set"),
        "Synthetic attestation; not a legal opinion",
        True,
        Currency.USD,
        trades,
        agreement,
    )
    book = PortfolioSnapshot(
        PortfolioId("synthetic-phase5"),
        PortfolioVersion("1"),
        today,
        Currency.USD,
        (Counterparty(CounterpartyId("synthetic-cp"), "Synthetic entity", (scope,)),),
    )
    ledger = CollateralAccount(
        CollateralAccountId("synthetic-ledger"),
        scope.netting_set_id,
        agreement.csa_id,
        today,
        (usd(5),),
        (
            CollateralMovement(
                CollateralMovementId("pending-call"), today, date(2025, 1, 3), usd(4)
            ),
        ),
    )
    run = RunContext(RiskRunId("synthetic-phase5"), datetime(2025, 1, 1, tzinfo=UTC), 42, "a" * 64)
    result = PortfolioService(DiscountingEngine(), create_logger("INFO", stream=sys.stderr)).value(
        book, market, run, (ledger,)
    )
    return {
        "is_sample": True,
        "portfolio": canonical_value(book),
        "ledger": canonical_value(ledger),
        "result": canonical_value(result),
    }


if __name__ == "__main__":
    print(json.dumps(example(), sort_keys=True, indent=2))
