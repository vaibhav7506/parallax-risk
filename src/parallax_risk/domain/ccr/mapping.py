"""Restricted supported-contract mapping; never infer eligibility from a pricing contract."""

from datetime import date

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.ccr.contracts import AssetClass, SupervisoryTrade
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import InterestRateSwap, SwapDirection
from parallax_risk.domain.portfolio.contracts import Trade, instrument_end
from parallax_risk.domain.pricing._numbers import money_value, priced_money, product
from parallax_risk.domain.pricing.engine import PricingContext


def map_trade(
    trade: Trade, as_of: date, currency: Currency, market: PricingContext
) -> SupervisoryTrade:
    """Vanilla reporting-currency IRS or FX with domestic quote leg and same-day spot."""
    if not isinstance(trade, Trade) or not isinstance(market, PricingContext):
        raise DomainValidationError("CCR mapping requires typed trade and pricing context")
    if market.snapshot.valuation_date != as_of or not trade.active(as_of):
        raise DomainValidationError("Map only active trades at the matching market origin")
    if trade.termination_date is not None:
        raise DomainValidationError("Prototype does not model scheduled termination/reset exposure")
    contract = trade.instrument
    maturity = year_fraction(as_of, instrument_end(contract), DayCount.ACT_365_FIXED)
    sign = 1.0 if trade.quantity > 0 else -1.0
    quantity = money_value(Money(trade.quantity.copy_abs(), currency))
    if isinstance(contract, InterestRateSwap):
        if (
            contract.notional.currency != currency
            or contract.floating_spread != 0
            or contract.floating_gearing != 1
        ):
            raise DomainValidationError(
                "Prototype supports only domestic vanilla zero-spread unit-gearing IRS"
            )
        start = max(
            0.0, year_fraction(as_of, contract.fixed_periods[0].start, DayCount.ACT_365_FIXED)
        )
        end = year_fraction(as_of, contract.fixed_periods[-1].end, DayCount.ACT_365_FIXED)
        notional = priced_money(product(money_value(contract.notional), quantity), currency)
        delta = sign if contract.direction == SwapDirection.PAY_FIXED else -sign
        return SupervisoryTrade(
            trade.trade_id,
            AssetClass.INTEREST_RATE,
            (currency,),
            notional,
            delta,
            maturity,
            start,
            end,
        )
    if isinstance(contract, FxForward):
        if contract.quote_currency != currency:
            raise DomainValidationError("Prototype FX requires its quote leg in reporting currency")
        spot = market.snapshot.fx_spot(contract.base_notional.currency, currency)
        if spot.value_date != as_of:
            raise DomainValidationError("Supervisory FX conversion requires explicit same-day spot")
        notional = priced_money(
            product(money_value(contract.base_notional), quantity, spot.rate), currency
        )
        delta = sign if contract.direction == FxDirection.BUY_BASE else -sign
        return SupervisoryTrade(
            trade.trade_id,
            AssetClass.FX,
            (contract.base_notional.currency, currency),
            notional,
            delta,
            maturity,
        )
    raise DomainValidationError(
        "CCR prototype supports only vanilla IRS and FX forwards; other contracts rejected"
    )
