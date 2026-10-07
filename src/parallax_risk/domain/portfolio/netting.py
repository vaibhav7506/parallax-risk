"""Legal-scope aggregation with explicit no-netting comparison and signed collateral."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import NettingSetId, TradeId
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.portfolio.collateral import (
    CollateralAccount,
    MarginCall,
    convert,
    margin_call,
)
from parallax_risk.domain.portfolio.contracts import NettingSet, positive
from parallax_risk.domain.pricing.engine import PricingContext


@dataclass(frozen=True, slots=True)
class TradeValue:
    """Signed quantity-adjusted NPV in the contract's pricing currency."""

    trade_id: TradeId
    value: Money

    def __post_init__(self) -> None:
        if not isinstance(self.trade_id, TradeId) or not isinstance(self.value, Money):
            raise DomainValidationError("Trade value requires typed identity and Money")


@dataclass(frozen=True, slots=True)
class NettingResult:
    """All values in set currency. Negative exposure is a nonnegative payable magnitude."""

    netting_set_id: NettingSetId
    as_of: date
    trade_values: tuple[TradeValue, ...]
    signed_value: Money
    no_netting_positive: Money
    no_netting_negative: Money
    net_positive: Money
    net_negative: Money
    collateralized_positive: Money
    collateralized_negative: Money
    margin: MarginCall | None


def aggregate(
    netting_set: NettingSet,
    trade_values: tuple[TradeValue, ...],
    market: PricingContext,
    account: CollateralAccount | None = None,
) -> NettingResult:
    """Aggregate exactly one legal scope; no cross-set/counterparty offsets."""
    if not isinstance(netting_set, NettingSet) or not isinstance(market, PricingContext):
        raise DomainValidationError("Netting requires validated set and pricing context")
    require_tuple(trade_values, TradeValue)
    marks = {mark.trade_id: mark for mark in trade_values}
    if len(marks) != len(trade_values) or set(marks) != {t.trade_id for t in netting_set.trades}:
        raise DomainValidationError("Provide exactly one value for every trade, without extras")
    as_of = require_date(market.snapshot.valuation_date)
    currency = netting_set.reporting_currency
    zero = Money(Decimal(0), currency)
    signed, gross_positive, gross_negative = zero, zero, zero
    converted: list[TradeValue] = []
    for trade in netting_set.trades:
        mark = marks[trade.trade_id]
        if mark.value.currency != trade.currency or (
            not trade.active(as_of) and mark.value.amount != 0
        ):
            raise DomainValidationError("Trade value currency/lifecycle is inconsistent")
        value = convert(mark.value, currency, market)
        converted.append(TradeValue(trade.trade_id, value))
        signed = signed + value
        gross_positive = gross_positive + positive(value)
        gross_negative = gross_negative + positive(-value)
    net_positive = positive(signed) if netting_set.netting_enforceable else gross_positive
    net_negative = positive(-signed) if netting_set.netting_enforceable else gross_negative
    margin = None
    collateral_positive, collateral_negative = net_positive, net_negative
    if netting_set.csa is None:
        if account is not None:
            raise DomainValidationError("Uncollateralized scope cannot accept a collateral account")
    else:
        if account is None or account.netting_set_id != netting_set.netting_set_id:
            raise DomainValidationError("CSA scope requires its own collateral account")
        margin = margin_call(signed, netting_set.csa, account, market)
        residual = signed - margin.settled_collateral
        collateral_positive, collateral_negative = positive(residual), positive(-residual)
    return NettingResult(
        netting_set.netting_set_id,
        as_of,
        tuple(converted),
        signed,
        gross_positive,
        gross_negative,
        net_positive,
        net_negative,
        collateral_positive,
        collateral_negative,
        margin,
    )
