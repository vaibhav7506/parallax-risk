"""Real deterministic pricer orchestration and legal-scope reconciliation."""

import io
import math
import subprocess
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import (
    CollateralAccountId,
    CounterpartyId,
    CsaId,
    NettingSetId,
)
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.portfolio.netting import TradeValue, aggregate
from parallax_risk.domain.pricing.engine import DiscountingEngine
from tests.fixtures.deterministic import VALUATION, YEAR_ONE, context, money
from tests.fixtures.portfolio import account, csa, netting, portfolio, run, trade


def service():
    return PortfolioService(DiscountingEngine(), create_logger("INFO", stream=io.StringIO()))


def test_multiple_scopes_counterparties_no_cross_netting():
    cp = portfolio().counterparties[0]
    receive = netting(trades=(trade(),))
    pay = netting(netting_set_id=NettingSetId("pay-set"), trades=(trade("pay", -80),))
    other = replace(
        cp,
        counterparty_id=CounterpartyId("other"),
        netting_sets=(
            netting(netting_set_id=NettingSetId("other-set"), trades=(trade("other", -200),)),
        ),
    )
    book = portfolio(counterparties=(replace(cp, netting_sets=(receive, pay)), other))
    result = service().value(book, context(discount_rate=0), run())
    assert result.signed_value == money(-180)
    assert result.positive_exposure == money(100)
    assert result.negative_exposure == money(280)
    assert result.portfolio_hash == book.snapshot_hash
    assert len(result.prices) == 3 and len(result.counterparties) == 2
    assert result == service().value(book, context(discount_rate=0), run())


def test_signed_quantity_and_portfolio_reporting_conversion():
    record = trade(
        instrument=replace(trade().instrument, amount=money(100, Currency.EUR)),
        quantity=Decimal(-2),
    )
    scope = netting(reporting_currency=Currency.EUR, trades=(record,))
    cp = replace(portfolio().counterparties[0], netting_sets=(scope,))
    result = service().value(portfolio(counterparties=(cp,)), context(), run())
    assert result.positive_exposure == money(0)
    assert result.negative_exposure == -result.signed_value
    assert float(result.signed_value.amount) == pytest.approx(-220 * math.exp(-0.03), rel=1e-14)


def test_synthetic_demo_stdout_replay():
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(root / "scripts/demo_portfolio.py")]
    first = subprocess.run(command, cwd=root, check=True, capture_output=True)
    second = subprocess.run(command, cwd=root, check=True, capture_output=True)
    assert first.stdout == second.stdout
    assert b'"is_sample": true' in first.stdout
    assert b"portfolio_completed" in first.stderr


def test_collateralized_lifecycle_and_cross_currency():
    cp = portfolio().counterparties[0]
    scope = netting(
        csa=csa(),
        trades=(
            trade(),
            trade("terminated", -80, termination_date=VALUATION, termination_reason="cancelled"),
            trade("matured", -20, instrument=replace(trade().instrument, payment_date=VALUATION)),
            trade(
                "foreign",
                50,
                instrument=replace(trade().instrument, amount=money(50, Currency.EUR)),
            ),
        ),
    )
    book = portfolio(counterparties=(replace(cp, netting_sets=(scope,)),))
    ledger = account(opening_balances=(money(88),))
    result = service().value(book, context(discount_rate=0), run(), (ledger,))
    # EUR curve still .03; explicitly reconcile against the real pricer, not a mock.
    expected = money(100) + money(str(50 * math.exp(-0.03))).scale(Decimal("1.1"))
    assert float(result.signed_value.amount) == pytest.approx(float(expected.amount), rel=1e-14)
    assert result.positive_exposure == result.signed_value - money(88)
    assert len(result.prices) == 2 and result.account_hashes == (ledger.account_hash,)
    empty = service().value(portfolio(counterparties=()), context(), run())
    assert empty.signed_value == empty.positive_exposure == money(0)
    inactive = netting(trades=(trade(termination_date=VALUATION, termination_reason="cancelled"),))
    with pytest.raises(DomainValidationError):
        aggregate(inactive, (TradeValue(inactive.trades[0].trade_id, money(1)),), context())


@pytest.mark.parametrize(
    "field", ["valuation_date", "npv", "market_snapshot_hash", "curve_set_hash", "instrument_hash"]
)
def test_reject_inconsistent_pricer_evidence(field):
    class BadPricer:
        def price(self, instrument, market):
            result = DiscountingEngine().price(instrument, market)
            wrong = (
                YEAR_ONE
                if field == "valuation_date"
                else money(1, Currency.EUR)
                if field == "npv"
                else "a" * 64
            )
            return replace(result, **{field: wrong})

    stream = io.StringIO()
    workflow = PortfolioService(BadPricer(), create_logger("INFO", stream=stream))
    with pytest.raises(DomainValidationError):
        workflow.value(portfolio(), context(), run())
    assert "portfolio_failed" in stream.getvalue()


def test_reject_mismatched_dates_payment_policy_and_accounts():
    for book, market in [
        (None, context()),
        (portfolio(), None),
        (portfolio(as_of=date(2025, 1, 2)), context()),
        (portfolio(), context(include_today=True)),
    ]:
        with pytest.raises(DomainValidationError):
            service().value(book, market, run())
    with pytest.raises(DomainValidationError):
        service().value(portfolio(), context(), run(), (account(),))
    cp = portfolio().counterparties[0]
    book = portfolio(counterparties=(replace(cp, netting_sets=(netting(csa=csa()),)),))
    for accounts in [(), (account(), account()), [account()]]:
        with pytest.raises(DomainValidationError):
            service().value(book, context(), run(), accounts)
    second = netting(
        netting_set_id=NettingSetId("other"), csa=csa(csa_id=CsaId("other")), trades=()
    )
    book = portfolio(counterparties=(replace(cp, netting_sets=(netting(csa=csa()), second)),))
    ledger2 = account(netting_set_id=NettingSetId("other"), csa_id=CsaId("other"))
    with pytest.raises(DomainValidationError):
        service().value(book, context(), run(), (account(), ledger2))
    ledger2 = replace(ledger2, account_id=CollateralAccountId("other"))
    assert service().value(book, context(), run(), (account(), ledger2)).account_hashes


def test_untyped_pricer_and_run_rejected():
    class UntypedPricer:
        def price(self, instrument, market):
            return None

    logger = create_logger("INFO", stream=io.StringIO())
    with pytest.raises(DomainValidationError):
        PortfolioService(UntypedPricer(), logger).value(portfolio(), context(), run())
    with pytest.raises(DomainValidationError):
        service().value(portfolio(), context(), None)
