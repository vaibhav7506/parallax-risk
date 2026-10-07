"""Injected deterministic portfolio valuation; owns no database, market feed or RNG."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from parallax_risk.application.context import RunContext
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError, ParallaxError
from parallax_risk.common.identifiers import CounterpartyId
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.portfolio.collateral import CollateralAccount, convert
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.portfolio.netting import NettingResult, TradeValue, aggregate
from parallax_risk.domain.pricing.engine import Instrument, PricingContext
from parallax_risk.domain.pricing.results import PricingResult


class PortfolioPricer(Protocol):
    """Existing deterministic pricing contract; adapters must preserve input evidence."""

    def price(self, instrument: Instrument, context: PricingContext) -> PricingResult:
        """Price a supported contract with complete input hashes."""
        ...


@dataclass(frozen=True, slots=True)
class CounterpartyResult:
    """Positive set risks added in portfolio currency, without cross-set netting."""

    counterparty_id: CounterpartyId
    netting_sets: tuple[NettingResult, ...]
    signed_value: Money
    positive_exposure: Money
    negative_exposure: Money


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    """Run-linked portfolio values, pricer evidence and immutable ledger fingerprints."""

    context: RunContext
    portfolio_hash: str
    market_hash: str
    curve_set_hash: str
    account_hashes: tuple[str, ...]
    prices: tuple[PricingResult, ...]
    counterparties: tuple[CounterpartyResult, ...]
    signed_value: Money
    positive_exposure: Money
    negative_exposure: Money


@dataclass(frozen=True, slots=True)
class PortfolioService:
    """Validate dates, complete scoped ledgers and pricer lineage before aggregation."""

    engine: PortfolioPricer
    logger: WorkflowLogger

    def value(
        self,
        portfolio: PortfolioSnapshot,
        market: PricingContext,
        run: RunContext,
        accounts: tuple[CollateralAccount, ...] = (),
    ) -> PortfolioResult:
        """Price only active booked trades; preserve quantity/sign and legal boundaries."""
        if not isinstance(run, RunContext):
            raise DomainValidationError("Portfolio run requires validated RunContext")
        self.logger.event("portfolio_started", run_id=str(run.run_id), outcome="started")
        try:
            result = self._value(portfolio, market, run, accounts)
        except ParallaxError as error:
            self.logger.event(
                "portfolio_failed",
                run_id=str(run.run_id),
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event("portfolio_completed", run_id=str(run.run_id), outcome="completed")
        return result

    def _value(
        self,
        portfolio: PortfolioSnapshot,
        market: PricingContext,
        run: RunContext,
        accounts: tuple[CollateralAccount, ...],
    ) -> PortfolioResult:
        if not isinstance(portfolio, PortfolioSnapshot) or not isinstance(market, PricingContext):
            raise DomainValidationError("Portfolio valuation requires validated inputs")
        if (
            portfolio.as_of != market.snapshot.valuation_date
            or market.include_valuation_date_payments
        ):
            raise DomainValidationError("Portfolio valuation uses matching end-of-day dates")
        require_tuple(accounts, CollateralAccount)
        ledgers = {a.netting_set_id: a for a in accounts}
        expected = {
            n.netting_set_id
            for c in portfolio.counterparties
            for n in c.netting_sets
            if n.csa is not None
        }
        if (
            len(ledgers) != len(accounts)
            or set(ledgers) != expected
            or len({a.account_id for a in accounts}) != len(accounts)
        ):
            raise DomainValidationError("Provide one uniquely identified ledger per CSA scope")
        market_hash = market.snapshot.snapshot_hash
        curve_hash = market.curves.curve_hash
        prices: list[PricingResult] = []
        counterparties: list[CounterpartyResult] = []
        zero = Money(Decimal(0), portfolio.reporting_currency)
        total, total_positive, total_negative = zero, zero, zero
        for counterparty in portfolio.counterparties:
            sets: list[NettingResult] = []
            signed, exposure, negative = zero, zero, zero
            for netting in counterparty.netting_sets:
                marks: list[TradeValue] = []
                for trade in netting.trades:
                    value = Money(Decimal(0), trade.currency)
                    if trade.active(portfolio.as_of):
                        price = self.engine.price(trade.instrument, market)
                        if (
                            not isinstance(price, PricingResult)
                            or price.valuation_date != portfolio.as_of
                            or price.currency != trade.currency
                            or price.market_snapshot_hash != market_hash
                            or price.curve_set_hash != curve_hash
                            or price.instrument_hash != content_hash(trade.instrument)
                        ):
                            raise DomainValidationError(
                                "Pricer returned inconsistent input evidence"
                            )
                        prices.append(price)
                        value = price.npv.scale(trade.quantity)
                    marks.append(TradeValue(trade.trade_id, value))
                result = aggregate(
                    netting, tuple(marks), market, ledgers.get(netting.netting_set_id)
                )
                sets.append(result)
                signed = signed + convert(result.signed_value, portfolio.reporting_currency, market)
                exposure = exposure + convert(
                    result.collateralized_positive, portfolio.reporting_currency, market
                )
                negative = negative + convert(
                    result.collateralized_negative, portfolio.reporting_currency, market
                )
            counterparties.append(
                CounterpartyResult(
                    counterparty.counterparty_id, tuple(sets), signed, exposure, negative
                )
            )
            total, total_positive, total_negative = (
                total + signed,
                total_positive + exposure,
                total_negative + negative,
            )
        return PortfolioResult(
            run,
            portfolio.snapshot_hash,
            market_hash,
            curve_hash,
            tuple(ledgers[key].account_hash for key in sorted(ledgers, key=str)),
            tuple(prices),
            tuple(counterparties),
            total,
            total_positive,
            total_negative,
        )
