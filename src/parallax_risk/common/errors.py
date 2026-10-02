"""Stable, typed failures; callers must never silently substitute results."""


class ParallaxError(Exception):
    """Base application/domain error with a safe, deliberately authored message."""


class DomainValidationError(ParallaxError, ValueError):
    """A domain value violates its declared contract."""


class CurrencyMismatchError(DomainValidationError):
    """Money arithmetic attempted without an explicit currency conversion."""


class ConventionError(DomainValidationError):
    """A date, calendar or rate convention is invalid or unsupported."""


class NumericalError(ParallaxError, ArithmeticError):
    """Non-finite, out-of-domain or inexact arithmetic cannot be accepted."""


class ConfigurationError(ParallaxError, ValueError):
    """Configuration cannot be used safely."""


class InfrastructureError(ParallaxError):
    """An external dependency failed without exposing its credentials."""
