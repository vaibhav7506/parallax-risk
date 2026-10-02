"""Checked binary64 pricing arithmetic and explicit Money conversion policy."""

import math
from decimal import Decimal

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import NumericalError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money


def money_value(value: Money) -> float:
    """Convert Decimal currency units to binary64 for the documented pricing model."""
    result = require_finite(float(value.amount), name="pricing amount")
    if result == 0 and value.amount != 0:
        raise NumericalError("Pricing amount conversion underflowed")
    return result


def priced_money(value: float, currency: Currency) -> Money:
    """Wrap the shortest round-trip decimal spelling of a finite binary64 result.

    No cent rounding is performed. This conversion does not claim exact-decimal
    quantitative computation, distinct from the exact Money arithmetic contract.
    """
    return Money(Decimal(str(require_finite(value, name="pricing result"))), currency)


def product(*values: float) -> float:
    """Multiply finite scalars, raising on overflow or nonzero-product underflow."""
    for value in values:
        require_finite(value, name="product input")
    result = require_finite(math.prod(values), name="pricing product")
    if result == 0 and all(value != 0 for value in values):
        raise NumericalError("Pricing product underflowed")
    return result


def total(values: tuple[float, ...]) -> float:
    """Accumulate cash-flow values with compensated summation and finite validation."""
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError):
        raise NumericalError("Cash-flow aggregation exceeded finite arithmetic") from None
    return require_finite(result, name="cash-flow sum")
