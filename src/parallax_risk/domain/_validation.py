"""Shared Phase 2 value-object contracts; no application workflow logic."""

from datetime import date

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import Identifier
from parallax_risk.common.time import year_fraction


def require_currency(value: Currency) -> None:
    """Require an actual supported Currency enum rather than an unvalidated string."""
    if not isinstance(value, Currency):
        raise DomainValidationError("An explicit Currency is required")


def require_token(value: str) -> None:
    """Validate case-sensitive index/name tokens using the identifier grammar."""
    Identifier(value)


def require_text(value: str) -> None:
    """Require nonblank descriptive metadata without silently trimming it."""
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError("Nonblank descriptive metadata is required")


def require_tuple[T](values: tuple[T, ...], kind: type[T], *, nonempty: bool = False) -> None:
    """Reject mutable collections, mismatched elements and missing required values."""
    if not isinstance(values, tuple) or (nonempty and not values):
        raise DomainValidationError("An immutable tuple of values is required")
    if any(not isinstance(item, kind) for item in values):
        raise DomainValidationError("Tuple contains an unsupported value type")


def positive_accrual(start: date, end: date, convention: DayCount) -> float:
    """Require a strictly positive accrual under the caller's day-count convention."""
    result = year_fraction(start, end, convention)
    if end <= start or result <= 0:
        raise DomainValidationError("Accrual interval must have positive declared year fraction")
    return result
