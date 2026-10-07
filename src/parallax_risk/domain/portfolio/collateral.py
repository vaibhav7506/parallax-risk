"""Cash collateral ledger, pending-aware calls and frozen MPOR scenarios."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import (
    CollateralAccountId,
    CollateralMovementId,
    CsaId,
    NettingSetId,
)
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import require_currency, require_tuple
from parallax_risk.domain.portfolio.csa import Csa, calendar_offset
from parallax_risk.domain.pricing.engine import PricingContext


def convert(value: Money, currency: Currency, market: PricingContext) -> Money:
    """Convert today's value using an explicit direct, settlement-adjusted FX quote.

    S(today)=S(spot-date)*Dquote(spot-date)/Dbase(spot-date). The binary64
    conversion factor is represented as Decimal(str(rate)); this is not exact FX.
    Haircuts and subsequent Money additions retain their separate exact contract.
    """
    if not isinstance(value, Money) or not isinstance(market, PricingContext):
        raise DomainValidationError("Conversion requires Money and validated pricing context")
    require_currency(currency)
    if value.currency == currency:
        return value
    spot = market.snapshot.fx_spot(value.currency, currency)
    base = market.curves.discount_curve(value.currency).discount(spot.value_date)
    quote = market.curves.discount_curve(currency).discount(spot.value_date)
    rate = require_finite(spot.rate * quote / base, name="collateral FX conversion")
    if rate <= 0:
        raise DomainValidationError("Collateral FX conversion must be positive")
    converted = value.scale(Decimal(str(rate)))
    return Money(converted.amount, currency)


@dataclass(frozen=True, slots=True)
class CollateralMovement:
    """Signed physical cash transfer: + received, - posted/returned by the bank.

    These are caller-confirmed contractual settlements, not automatic real payments.
    No failed settlement, dispute, interest or rounding policy is inferred.
    """

    movement_id: CollateralMovementId
    call_date: date
    settlement_date: date
    amount: Money

    def __post_init__(self) -> None:
        if not isinstance(self.movement_id, CollateralMovementId):
            raise DomainValidationError("Movement ID must be typed")
        require_date(self.call_date)
        require_date(self.settlement_date)
        if self.settlement_date < self.call_date:
            raise DomainValidationError("Settlement cannot precede collateral call")
        if not isinstance(self.amount, Money) or self.amount.amount == 0:
            raise DomainValidationError("A movement must transfer nonzero Money")


@dataclass(frozen=True, slots=True)
class CollateralAccount:
    """Immutable opening cash balances plus a dated physical movement timeline."""

    account_id: CollateralAccountId
    netting_set_id: NettingSetId
    csa_id: CsaId
    opening_date: date
    opening_balances: tuple[Money, ...]
    movements: tuple[CollateralMovement, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.account_id, CollateralAccountId)
            or not isinstance(self.netting_set_id, NettingSetId)
            or not isinstance(self.csa_id, CsaId)
        ):
            raise DomainValidationError("Collateral account identities must be typed")
        require_date(self.opening_date)
        require_tuple(self.opening_balances, Money)
        require_tuple(self.movements, CollateralMovement)
        if len({m.currency for m in self.opening_balances}) != len(self.opening_balances):
            raise DomainValidationError("Duplicate opening balance currency")
        if len({m.movement_id for m in self.movements}) != len(self.movements):
            raise DomainValidationError("Duplicate collateral movement ID")
        if any(m.call_date < self.opening_date for m in self.movements):
            raise DomainValidationError("Movement cannot predate account opening")
        object.__setattr__(
            self, "opening_balances", tuple(sorted(self.opening_balances, key=lambda m: m.currency))
        )
        object.__setattr__(
            self,
            "movements",
            tuple(
                sorted(
                    self.movements,
                    key=lambda m: (m.call_date, m.settlement_date, str(m.movement_id)),
                )
            ),
        )

    def balances(self, as_of: date, *, include_pending: bool = False) -> tuple[Money, ...]:
        """End-of-day balances; known pending calls are included only when requested.

        Calls after as_of are never known in a historical projection. Settlements
        on as_of count; opening balances are effective at opening-day start.
        """
        require_date(as_of)
        if as_of < self.opening_date or type(include_pending) is not bool:
            raise DomainValidationError("Balance date/pending policy is invalid")
        values = {m.currency: m for m in self.opening_balances}
        for movement in self.movements:
            if movement.call_date <= as_of and (
                include_pending or movement.settlement_date <= as_of
            ):
                cash = movement.amount
                values[cash.currency] = (
                    values.get(cash.currency, Money(Decimal(0), cash.currency)) + cash
                )
        return tuple(values[currency] for currency in sorted(values))

    def append(self, movement: CollateralMovement) -> "CollateralAccount":
        """Return a new ledger; original history and IDs remain unchanged."""
        if not isinstance(movement, CollateralMovement):
            raise DomainValidationError("Append requires a validated movement")
        return replace(self, movements=(*self.movements, movement))

    @property
    def account_hash(self) -> str:
        """Digest retains both pending and settled movement evidence."""
        return content_hash(self)


def collateral_value(balances: tuple[Money, ...], csa: Csa, market: PricingContext) -> Money:
    """Signed haircut-adjusted value; positive collateral reduces bank exposure."""
    require_tuple(balances, Money)
    if not isinstance(csa, Csa) or not isinstance(market, PricingContext):
        raise DomainValidationError("Collateral valuation requires CSA and pricing context")
    if len({b.currency for b in balances}) != len(balances):
        raise DomainValidationError("Collateral balances must have unique currencies")
    value = Money(Decimal(0), csa.currency)
    for balance in balances:
        csa.validate_direction(balance)
        haircut = csa.eligible(balance.currency).valuation_factor
        value = value + convert(balance.scale(haircut), csa.currency, market)
    return value


def validate_account(account: CollateralAccount, csa: Csa, market: PricingContext) -> None:
    """Check agreement ownership, eligibility, lag and every historical cash state."""
    if (
        not isinstance(account, CollateralAccount)
        or not isinstance(csa, Csa)
        or not isinstance(market, PricingContext)
    ):
        raise DomainValidationError("Account, CSA and market must be typed")
    if account.csa_id != csa.csa_id:
        raise DomainValidationError("Collateral account belongs to another CSA")
    for movement in account.movements:
        csa.eligible(movement.amount.currency)
        if not csa.margin_date(movement.call_date) or movement.settlement_date != calendar_offset(
            movement.call_date, csa.settlement_lag_days
        ):
            raise DomainValidationError("Movement violates CSA schedule/settlement lag")
    dates = {account.opening_date, *(m.settlement_date for m in account.movements)}
    for as_of in sorted(dates):
        collateral_value(account.balances(as_of), csa, market)


@dataclass(frozen=True, slots=True)
class MarginCall:
    """Effective agreement-currency amounts; physical denomination is caller allocated.

    Equality with MTA suppresses the transfer. An executed call transfers the full
    difference, not difference minus MTA. No nominal-cash inverse FX/rounding is inferred.
    """

    as_of: date
    variation_margin_target: Money
    total_target: Money
    settled_collateral: Money
    projected_collateral: Money
    transfer: Money
    settlement_date: date
    on_schedule: bool
    account_hash: str


def margin_call(
    value: Money, csa: Csa, account: CollateralAccount, market: PricingContext
) -> MarginCall:
    """Issue a research effective-value instruction without mutating the cash ledger."""
    validate_account(account, csa, market)
    as_of = market.snapshot.valuation_date
    vm, target = csa.target(value)
    settled = collateral_value(account.balances(as_of), csa, market)
    projected = collateral_value(account.balances(as_of, include_pending=True), csa, market)
    csa.validate_direction(projected)
    difference = target - projected
    scheduled = csa.margin_date(as_of)
    transfer = (
        difference
        if scheduled and difference.amount.copy_abs() > csa.minimum_transfer_amount.amount
        else Money(Decimal(0), csa.currency)
    )
    return MarginCall(
        as_of,
        vm,
        target,
        settled,
        projected,
        transfer,
        calendar_offset(as_of, csa.settlement_lag_days),
        scheduled,
        account.account_hash,
    )


@dataclass(frozen=True, slots=True)
class MporScenario:
    """Deterministic caller-valued closeout scenario, not a stochastic/default model."""

    default_date: date
    closeout_date: date
    frozen_balances: tuple[Money, ...]
    collateral_at_closeout: Money
    residual_value: Money
    positive_exposure: Money
    account_hash: str
    market_hash: str


def mpor_scenario(
    value_at_closeout: Money,
    csa: Csa,
    account: CollateralAccount,
    default_date: date,
    closeout_market: PricingContext,
) -> MporScenario:
    """Freeze physical settled balances at default; revalue their FX at MPOR endpoint.

    Ignore all subsequent calls/settlements, including pre-default pending calls.
    No margin interest, liquidation costs, disputes or legal closeout recovery.
    Caller supplies the portfolio value at exactly default + declared calendar MPOR.
    """
    validate_account(account, csa, closeout_market)
    endpoint = calendar_offset(default_date, csa.margin_period_of_risk_days)
    if closeout_market.snapshot.valuation_date != endpoint:
        raise DomainValidationError("MPOR market must be dated at the exact closeout endpoint")
    if not isinstance(value_at_closeout, Money) or value_at_closeout.currency != csa.currency:
        raise DomainValidationError("Closeout value must use agreement currency")
    frozen = account.balances(default_date)
    collateral = collateral_value(frozen, csa, closeout_market)
    residual = value_at_closeout - collateral
    exposure = residual if residual.amount > 0 else Money(Decimal(0), csa.currency)
    return MporScenario(
        default_date,
        endpoint,
        frozen,
        collateral,
        residual,
        exposure,
        account.account_hash,
        closeout_market.snapshot.snapshot_hash,
    )
