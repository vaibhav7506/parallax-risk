"""Portfolio snapshots; lifecycle eligibility never infers legal enforceability."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import (
    CounterpartyId,
    NettingSetId,
    PortfolioId,
    PortfolioVersion,
    TradeId,
)
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_currency, require_text, require_tuple
from parallax_risk.domain.instruments.cashflows import (
    CashFlow,
    FixedRateCashFlow,
    FloatingRateCashFlow,
)
from parallax_risk.domain.instruments.fx.contracts import FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    ZeroCouponBond,
)
from parallax_risk.domain.portfolio.csa import Csa
from parallax_risk.domain.pricing.engine import Instrument


def instrument_end(instrument: Instrument) -> date:
    """Last contractual payment date, including payment lag on supplied schedules."""
    if isinstance(instrument, CashFlow):
        return instrument.payment_date
    if isinstance(instrument, (FixedRateCashFlow, FloatingRateCashFlow)):
        return instrument.period.payment_date
    if isinstance(instrument, (ZeroCouponBond, FxForward)):
        return instrument.maturity
    if isinstance(instrument, FixedRateBond):
        return instrument.periods[-1].payment_date
    if isinstance(instrument, InterestRateSwap):
        return max(
            instrument.fixed_periods[-1].payment_date, instrument.floating_periods[-1].payment_date
        )
    raise DomainValidationError("Unsupported portfolio instrument")


def instrument_currency(instrument: Instrument) -> Currency:
    """Currency of the existing deterministic engine's NPV."""
    if isinstance(instrument, CashFlow):
        return instrument.amount.currency
    if isinstance(instrument, (FixedRateCashFlow, FloatingRateCashFlow, InterestRateSwap)):
        return instrument.notional.currency
    if isinstance(instrument, FxForward):
        return instrument.quote_currency
    if isinstance(instrument, (ZeroCouponBond, FixedRateBond)):
        return instrument.face_value.currency
    raise DomainValidationError("Unsupported portfolio instrument")


@dataclass(frozen=True, slots=True)
class Trade:
    """Signed position in an existing contract; active from booking until exit/payment.

    Effective date is metadata, not an activation gate: forward-start contracts
    can have value before their contractual start. Termination assumes all exit
    payments are booked as separate trades; no cancellation/novation cash is inferred.
    """

    trade_id: TradeId
    instrument: Instrument
    quantity: Decimal
    booking_date: date
    effective_date: date
    termination_date: date | None = None
    termination_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.trade_id, TradeId) or not isinstance(
            self.instrument,
            (
                CashFlow,
                FixedRateCashFlow,
                FloatingRateCashFlow,
                ZeroCouponBond,
                FixedRateBond,
                InterestRateSwap,
                FxForward,
            ),
        ):
            raise DomainValidationError("Trade requires a typed ID and supported contract")
        if (
            not isinstance(self.quantity, Decimal)
            or not self.quantity.is_finite()
            or self.quantity == 0
        ):
            raise DomainValidationError("Trade quantity must be nonzero finite Decimal")
        require_date(self.booking_date)
        require_date(self.effective_date)
        if not self.booking_date <= self.effective_date <= instrument_end(self.instrument):
            raise DomainValidationError("Booking/effective/payment dates must be ordered")
        if self.termination_date is None:
            if self.termination_reason is not None:
                raise DomainValidationError("Termination reason requires a termination date")
        else:
            require_date(self.termination_date)
            if not self.booking_date <= self.termination_date <= instrument_end(self.instrument):
                raise DomainValidationError("Termination must lie within the booked lifecycle")
            if not isinstance(self.termination_reason, str):
                raise DomainValidationError("Termination requires an explicit reason")
            require_text(self.termination_reason)

    def active(self, as_of: date) -> bool:
        """End-of-day cutoff: payment/termination on valuation day is excluded."""
        require_date(as_of)
        return self.booking_date <= as_of < instrument_end(self.instrument) and (
            self.termination_date is None or as_of < self.termination_date
        )

    @property
    def currency(self) -> Currency:
        """Contract NPV currency; FX trades additionally carry their base currency."""
        return instrument_currency(self.instrument)


@dataclass(frozen=True, slots=True)
class NettingSet:
    """Caller-attested legal scope. Disabling netting preserves gross positive risk."""

    netting_set_id: NettingSetId
    agreement_reference: str
    netting_enforceable: bool
    reporting_currency: Currency
    trades: tuple[Trade, ...]
    csa: Csa | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.netting_set_id, NettingSetId):
            raise DomainValidationError("Netting set ID must be typed")
        require_text(self.agreement_reference)
        require_currency(self.reporting_currency)
        if type(self.netting_enforceable) is not bool:
            raise DomainValidationError("Netting enforceability must be explicit boolean")
        require_tuple(self.trades, Trade)
        if len({trade.trade_id for trade in self.trades}) != len(self.trades):
            raise DomainValidationError("Trade IDs must be unique in a netting set")
        if self.csa is not None and (
            not isinstance(self.csa, Csa)
            or not self.netting_enforceable
            or self.csa.currency != self.reporting_currency
        ):
            raise DomainValidationError("CSA requires enforceable netting and matching currency")
        object.__setattr__(
            self, "trades", tuple(sorted(self.trades, key=lambda t: str(t.trade_id)))
        )


@dataclass(frozen=True, slots=True)
class Counterparty:
    """Separate legal entity; never net values across its different legal scopes."""

    counterparty_id: CounterpartyId
    legal_name: str
    netting_sets: tuple[NettingSet, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.counterparty_id, CounterpartyId):
            raise DomainValidationError("Counterparty ID must be typed")
        require_text(self.legal_name)
        require_tuple(self.netting_sets, NettingSet)
        if len({n.netting_set_id for n in self.netting_sets}) != len(self.netting_sets):
            raise DomainValidationError("Duplicate netting set ID")
        object.__setattr__(
            self,
            "netting_sets",
            tuple(sorted(self.netting_sets, key=lambda n: str(n.netting_set_id))),
        )


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Content-addressed immutable end-of-day book, including legal/CSA metadata."""

    portfolio_id: PortfolioId
    version: PortfolioVersion
    as_of: date
    reporting_currency: Currency
    counterparties: tuple[Counterparty, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.portfolio_id, PortfolioId) or not isinstance(
            self.version, PortfolioVersion
        ):
            raise DomainValidationError("Portfolio ID/version must be typed")
        require_date(self.as_of)
        require_currency(self.reporting_currency)
        require_tuple(self.counterparties, Counterparty)
        sets = tuple(n for c in self.counterparties for n in c.netting_sets)
        trades = tuple(t for n in sets for t in n.trades)
        for identities in (
            tuple(c.counterparty_id for c in self.counterparties),
            tuple(n.netting_set_id for n in sets),
            tuple(t.trade_id for t in trades),
            tuple(n.csa.csa_id for n in sets if n.csa is not None),
        ):
            if len(set(identities)) != len(identities):
                raise DomainValidationError("Portfolio scope, trade and CSA IDs must be unique")
        if any(t.booking_date > self.as_of for t in trades):
            raise DomainValidationError("A snapshot cannot contain trades booked in the future")
        object.__setattr__(
            self,
            "counterparties",
            tuple(sorted(self.counterparties, key=lambda c: str(c.counterparty_id))),
        )

    @property
    def snapshot_hash(self) -> str:
        """Digest includes version, dates, full contracts and enforceability attestation."""
        return content_hash(self)


def positive(value: Money) -> Money:
    """Positive currency units with no decimal context rounding."""
    if not isinstance(value, Money):
        raise DomainValidationError("Positive part requires Money")
    return value if value.amount > 0 else Money(Decimal(0), value.currency)
