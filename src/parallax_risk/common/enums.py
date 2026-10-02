"""Explicit supported currencies and financial conventions."""

from enum import StrEnum


class Currency(StrEnum):
    """Supported ISO 4217 codes; this is an explicit subset, not a full registry."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    INR = "INR"
    CNY = "CNY"


class DayCount(StrEnum):
    """Named conventions; 30E/360 is European, not US or ISDA-maturity variant."""

    ACT_360 = "ACT/360"
    ACT_365_FIXED = "ACT/365F"
    ACT_ACT_ISDA = "ACT/ACT ISDA"
    THIRTY_E_360 = "30E/360"


class BusinessDayConvention(StrEnum):
    """Date adjustment, with calendar explicitly supplied by the caller."""

    UNADJUSTED = "unadjusted"
    FOLLOWING = "following"
    MODIFIED_FOLLOWING = "modified_following"
    PRECEDING = "preceding"
    MODIFIED_PRECEDING = "modified_preceding"


class Compounding(StrEnum):
    """Accumulation conventions for decimal annual rates and year fractions."""

    SIMPLE = "simple"
    CONTINUOUS = "continuous"
    PERIODIC = "periodic"
