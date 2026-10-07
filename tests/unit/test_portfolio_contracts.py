"""Reject invalid legal scopes, lifecycle metadata and CSA conventions."""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal

import pytest

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CounterpartyId, CsaId, NettingSetId, PortfolioVersion
from parallax_risk.domain.instruments.cashflows import FixedRateCashFlow, FloatingRateCashFlow
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    SwapDirection,
    ZeroCouponBond,
)
from parallax_risk.domain.portfolio.contracts import (
    Counterparty,
    instrument_currency,
    instrument_end,
    positive,
)
from parallax_risk.domain.portfolio.csa import (
    CollateralDirection,
    EligibleCollateral,
    calendar_offset,
)
from tests.fixtures.deterministic import INDEX, PERIODS, VALUATION, YEAR_ONE, YEAR_TWO, money
from tests.fixtures.portfolio import csa, netting, portfolio, trade


@pytest.mark.parametrize(
    "instrument,currency,end",
    [
        (ZeroCouponBond(money(), YEAR_ONE), Currency.USD, YEAR_ONE),
        (FixedRateBond(money(), 0.03, PERIODS, DayCount.ACT_365_FIXED), Currency.USD, YEAR_TWO),
        (
            InterestRateSwap(
                money(),
                0.03,
                PERIODS,
                PERIODS,
                (VALUATION, YEAR_ONE),
                INDEX,
                DayCount.ACT_365_FIXED,
                DayCount.ACT_365_FIXED,
                SwapDirection.PAY_FIXED,
            ),
            Currency.USD,
            YEAR_TWO,
        ),
        (
            FxForward(
                money(currency=Currency.EUR),
                Currency.USD,
                Decimal("1.1"),
                YEAR_ONE,
                FxDirection.BUY_BASE,
            ),
            Currency.USD,
            YEAR_ONE,
        ),
        (
            FixedRateCashFlow(money(), 0.03, PERIODS[0], DayCount.ACT_365_FIXED),
            Currency.USD,
            YEAR_ONE,
        ),
        (
            FloatingRateCashFlow(money(), PERIODS[0], VALUATION, INDEX, DayCount.ACT_365_FIXED),
            Currency.USD,
            YEAR_ONE,
        ),
    ],
)
def test_contract_currency_and_last_payment(instrument, currency, end):
    record = trade(instrument=instrument)
    assert record.currency == instrument_currency(instrument) == currency
    assert instrument_end(instrument) == end
    assert record.active(VALUATION)
    assert not record.active(end)


def test_forward_start_termination_and_hash_immutability():
    record = trade(effective_date=date(2025, 6, 1))
    assert record.active(VALUATION)
    assert not record.active(date(2024, 12, 31))
    exited = replace(record, termination_date=date(2025, 3, 1), termination_reason="novation")
    assert exited.active(date(2025, 2, 28)) and not exited.active(date(2025, 3, 1))
    book = portfolio()
    assert book.snapshot_hash != replace(book, version=PortfolioVersion("2")).snapshot_hash
    assert (
        book.snapshot_hash
        != portfolio(
            counterparties=(
                replace(book.counterparties[0], netting_sets=(netting(netting_enforceable=False),)),
            )
        ).snapshot_hash
    )
    with pytest.raises(FrozenInstanceError):
        book.as_of = YEAR_ONE


@pytest.mark.parametrize(
    "changes",
    [
        {"trade_id": "untyped"},
        {"instrument": None},
        {"quantity": 1},
        {"quantity": Decimal(0)},
        {"quantity": Decimal("NaN")},
        {"quantity": Decimal("Infinity")},
        {"effective_date": date(2024, 1, 1)},
        {"effective_date": YEAR_TWO},
        {"termination_reason": "missing date"},
        {"termination_date": date(2024, 1, 1)},
        {"termination_date": YEAR_TWO},
        {"termination_date": YEAR_ONE},
        {"termination_date": YEAR_ONE, "termination_reason": " "},
    ],
)
def test_invalid_trade(changes):
    with pytest.raises(DomainValidationError):
        trade(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"netting_set_id": "untyped"},
        {"agreement_reference": " "},
        {"netting_enforceable": 1},
        {"reporting_currency": "USD"},
        {"trades": [trade()]},
        {"trades": (trade(), trade())},
        {"csa": "untyped"},
        {"csa": csa(), "netting_enforceable": False},
        {"csa": csa(), "reporting_currency": Currency.EUR},
    ],
)
def test_invalid_netting(changes):
    with pytest.raises(DomainValidationError):
        netting(**changes)


def test_counterparty_and_global_identity_validation():
    for identity, name, sets in [
        ("untyped", "name", ()),
        (CounterpartyId("cp"), " ", ()),
        (CounterpartyId("cp"), "name", (netting(), netting())),
    ]:
        with pytest.raises(DomainValidationError):
            Counterparty(identity, name, sets)
    book = portfolio()
    cp = book.counterparties[0]
    candidates = [
        (cp, cp),
        (cp, replace(cp, counterparty_id=CounterpartyId("other"))),
        (
            cp,
            replace(
                cp,
                counterparty_id=CounterpartyId("other"),
                netting_sets=(netting(netting_set_id=NettingSetId("other")),),
            ),
        ),
    ]
    for counterparties in candidates:
        with pytest.raises(DomainValidationError):
            portfolio(counterparties=counterparties)
    first = netting(csa=csa(), trades=())
    second = netting(netting_set_id=NettingSetId("other"), csa=csa(), trades=())
    with pytest.raises(DomainValidationError):
        portfolio(counterparties=(replace(cp, netting_sets=(first, second)),))
    with pytest.raises(DomainValidationError):
        portfolio(portfolio_id="untyped")
    with pytest.raises(DomainValidationError):
        portfolio(version="untyped")
    with pytest.raises(DomainValidationError):
        portfolio(as_of=date(2024, 12, 31))
    # Empty research portfolios and legal scopes are valid and canonically ordered.
    other = replace(cp, counterparty_id=CounterpartyId("a"), netting_sets=())
    assert (
        portfolio(counterparties=(cp, other)).snapshot_hash
        == portfolio(counterparties=(other, cp)).snapshot_hash
    )
    assert netting(trades=tuple(reversed(netting().trades))) == netting()
    assert replace(cp, netting_sets=())


@pytest.mark.parametrize(
    "changes",
    [
        {"csa_id": "untyped"},
        {"currency": "USD"},
        {"receive_threshold": money(-1)},
        {"post_threshold": money(-1)},
        {"minimum_transfer_amount": money(-1)},
        {"independent_amount": money(1, Currency.EUR)},
        {"receive_threshold": 1},
        {"direction": "two_way"},
        {"eligible_collateral": ()},
        {"eligible_collateral": (EligibleCollateral(Currency.USD, Decimal(0)),) * 2},
        {"frequency_days": 0},
        {"frequency_days": True},
        {"settlement_lag_days": -1},
        {"margin_period_of_risk_days": 1.5},
        {"settlement_lag_days": 10**12},
        {"direction": CollateralDirection.RECEIVE_ONLY, "independent_amount": money(-1)},
        {"direction": CollateralDirection.POST_ONLY, "independent_amount": money(1)},
    ],
)
def test_invalid_csa(changes):
    with pytest.raises(DomainValidationError):
        csa(**changes)


@pytest.mark.parametrize(
    "haircut", [-1, Decimal(-1), Decimal(1), Decimal("NaN"), Decimal("Infinity")]
)
def test_invalid_haircut(haircut):
    with pytest.raises(DomainValidationError):
        EligibleCollateral(Currency.USD, haircut)


def test_calendar_eligibility_and_target_boundaries():
    agreement = csa(first_margin_date=YEAR_ONE, frequency_days=3)
    assert not agreement.margin_date(VALUATION)
    assert agreement.margin_date(YEAR_ONE)
    assert not agreement.margin_date(date(2026, 1, 2))
    assert agreement.target(money(10)) == (money(0), money(0))
    assert agreement.target(money(-20)) == (money(0), money(0))
    for value in [money(currency=Currency.EUR), None]:
        with pytest.raises(DomainValidationError):
            agreement.target(value)
    with pytest.raises(DomainValidationError):
        agreement.eligible(Currency.GBP)
    with pytest.raises(DomainValidationError):
        calendar_offset(VALUATION, True)
    with pytest.raises(DomainValidationError):
        calendar_offset(VALUATION, -1)
    with pytest.raises(DomainValidationError):
        calendar_offset(date.max, 1)
    assert csa(csa_id=CsaId("other")).csa_id != agreement.csa_id


def test_public_instrument_helpers_reject_unsupported_values():
    for helper in (instrument_end, instrument_currency, positive):
        with pytest.raises(DomainValidationError):
            helper(None)
