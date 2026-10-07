"""Explicit synthetic Phase 5 book and title-transfer CSA; no observed data."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

from parallax_risk.application.context import RunContext
from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import (
    CollateralAccountId,
    CounterpartyId,
    CsaId,
    NettingSetId,
    PortfolioId,
    PortfolioVersion,
    RiskRunId,
    TradeId,
)
from parallax_risk.domain.instruments.cashflows import CashFlow
from parallax_risk.domain.portfolio.collateral import CollateralAccount
from parallax_risk.domain.portfolio.contracts import (
    Counterparty,
    NettingSet,
    PortfolioSnapshot,
    Trade,
)
from parallax_risk.domain.portfolio.csa import CollateralDirection, Csa, EligibleCollateral
from tests.fixtures.deterministic import VALUATION, YEAR_ONE, money


def csa(**changes):
    return replace(
        Csa(
            CsaId("synthetic-csa"),
            Currency.USD,
            money(10),
            money(20),
            money(5),
            money(0),
            (
                EligibleCollateral(Currency.USD, Decimal(0)),
                EligibleCollateral(Currency.EUR, Decimal("0.2")),
            ),
            CollateralDirection.TWO_WAY,
            VALUATION,
            1,
            2,
            10,
        ),
        **changes,
    )


def account(**changes):
    return replace(
        CollateralAccount(
            CollateralAccountId("synthetic-ledger"),
            NettingSetId("synthetic-set"),
            CsaId("synthetic-csa"),
            VALUATION,
            (),
        ),
        **changes,
    )


def trade(name="receive", amount=100, **changes):
    return replace(
        Trade(TradeId(name), CashFlow(YEAR_ONE, money(amount)), Decimal(1), VALUATION, VALUATION),
        **changes,
    )


def netting(**changes):
    return replace(
        NettingSet(
            NettingSetId("synthetic-set"),
            "synthetic legal attestation",
            True,
            Currency.USD,
            (trade(), trade("pay", -80)),
        ),
        **changes,
    )


def portfolio(**changes):
    return replace(
        PortfolioSnapshot(
            PortfolioId("synthetic-book"),
            PortfolioVersion("1"),
            VALUATION,
            Currency.USD,
            (Counterparty(CounterpartyId("synthetic-cp"), "Synthetic legal entity", (netting(),)),),
        ),
        **changes,
    )


def run():
    return RunContext(RiskRunId("synthetic-phase5"), datetime(2025, 1, 1, tzinfo=UTC), 42, "a" * 64)


def dated_market(market, as_of: date):
    """Shift explicit market/curve anchors only for zero-rate synthetic timeline tests."""
    return replace(
        market,
        snapshot=replace(
            market.snapshot,
            valuation_date=as_of,
            fx_spots=tuple(replace(s, value_date=as_of) for s in market.snapshot.fx_spots),
        ),
        curves=replace(
            market.curves,
            discount_curves=tuple(
                replace(c, valuation_date=as_of) for c in market.curves.discount_curves
            ),
            forward_curves=tuple(
                replace(f, curve=replace(f.curve, valuation_date=as_of))
                for f in market.curves.forward_curves
            ),
        ),
    )
