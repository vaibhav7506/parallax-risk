"""Exact decimal money; no implicit FX, float conversion or cent rounding."""

from dataclasses import dataclass
from decimal import Context, Decimal, DecimalException, Inexact, localcontext

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import CurrencyMismatchError, DomainValidationError, NumericalError


def _decimal(value: Decimal) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise DomainValidationError("Money amounts and scalars must be finite Decimal values")


@dataclass(frozen=True, slots=True)
class Money:
    """Signed currency units, exact to at most 34 significant arithmetic digits.

    Positive denotes a receivable/asset; negative denotes a payable/liability.
    Precision loss raises an error instead of silently rounding. Input values are
    preserved exactly; settlement rounding belongs to an explicit later policy.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        _decimal(self.amount)
        if not isinstance(self.currency, Currency):
            raise DomainValidationError("Money currency must be an explicit Currency")

    def _combine(self, other: "Money", *, subtract: bool) -> "Money":
        if not isinstance(other, Money):
            raise DomainValidationError("Money arithmetic requires Money")
        if self.currency != other.currency:
            raise CurrencyMismatchError("Explicit FX conversion required for different currencies")
        try:
            with localcontext(Context(prec=34)) as context:
                context.traps[Inexact] = True
                amount = self.amount - other.amount if subtract else self.amount + other.amount
        except DecimalException:
            raise NumericalError("Money arithmetic exceeded exact decimal precision") from None
        return Money(amount, self.currency)

    def __add__(self, other: "Money") -> "Money":
        """Add like-currency units with exact decimal arithmetic."""
        return self._combine(other, subtract=False)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract like-currency units with exact decimal arithmetic."""
        return self._combine(other, subtract=True)

    def __neg__(self) -> "Money":
        """Reverse the receivable/payable sign without rounding."""
        return Money(self.amount.copy_negate(), self.currency)

    def scale(self, factor: Decimal) -> "Money":
        """Multiply by an explicit finite decimal scalar, rejecting precision loss."""
        _decimal(factor)
        try:
            with localcontext(Context(prec=34)) as context:
                context.traps[Inexact] = True
                amount = self.amount * factor
        except DecimalException:
            raise NumericalError("Money scaling exceeded exact decimal precision") from None
        return Money(amount, self.currency)
