"""Civil dates, aware UTC instants, declared calendars and day counts."""

import calendar as year_calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from parallax_risk.common.enums import BusinessDayConvention, DayCount
from parallax_risk.common.errors import ConventionError


def require_date(value: date) -> date:
    """Accept a pure civil date; datetime is deliberately rejected."""
    if type(value) is not date:
        raise ConventionError("Expected a civil date without time or timezone")
    return value


def utc_timestamp(value: datetime) -> datetime:
    """Normalize an aware instant to UTC; never infer a missing timezone."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ConventionError("Timestamp must have an explicit timezone")
    return value.astimezone(UTC)


class BusinessCalendar(Protocol):
    """Port for market-specific calendars; no holiday feed is implicitly trusted."""

    def is_business_day(self, value: date) -> bool:
        """Return whether a civil date is open for business."""
        ...


@dataclass(frozen=True, slots=True)
class HolidayCalendar:
    """User-supplied holidays and Python weekday numbers (Monday=0).

    Default weekends are Saturday/Sunday, not an official exchange calendar.
    Name and frozen holiday content must be versioned by the caller later.
    """

    name: str
    holidays: frozenset[date] = frozenset()
    weekend_days: frozenset[int] = frozenset({5, 6})

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConventionError("Calendar name is required")
        if not isinstance(self.holidays, frozenset) or not isinstance(self.weekend_days, frozenset):
            raise ConventionError("Calendar collections must be immutable frozensets")
        if len(self.weekend_days) == 7 or any(
            type(day) is not int or not 0 <= day <= 6 for day in self.weekend_days
        ):
            raise ConventionError("Weekend days must be 0–6 with at least one open weekday")
        for holiday in self.holidays:
            require_date(holiday)

    def is_business_day(self, value: date) -> bool:
        """Evaluate a date against the explicit weekend and holiday sets."""
        require_date(value)
        return value.weekday() not in self.weekend_days and value not in self.holidays


def _step(value: date, days: int) -> date:
    try:
        return value + timedelta(days=days)
    except OverflowError:
        raise ConventionError("Calendar operation exceeded supported civil date range") from None


def _seek(value: date, calendar: BusinessCalendar, direction: int) -> date:
    while not calendar.is_business_day(value):
        value = _step(value, direction)
    return value


def adjust_business_day(
    value: date, calendar: BusinessCalendar, convention: BusinessDayConvention
) -> date:
    """Adjust a civil date; modified conventions preserve its calendar month."""
    require_date(value)
    if not isinstance(convention, BusinessDayConvention):
        raise ConventionError("Unsupported business-day convention")
    if convention == BusinessDayConvention.UNADJUSTED:
        return value
    following = convention in {
        BusinessDayConvention.FOLLOWING,
        BusinessDayConvention.MODIFIED_FOLLOWING,
    }
    adjusted = _seek(value, calendar, 1 if following else -1)
    modified = convention in {
        BusinessDayConvention.MODIFIED_FOLLOWING,
        BusinessDayConvention.MODIFIED_PRECEDING,
    }
    if modified and adjusted.month != value.month:
        return _seek(value, calendar, -1 if following else 1)
    return adjusted


def add_business_days(value: date, days: int, calendar: BusinessCalendar) -> date:
    """Count business days excluding the start; zero preserves the input date."""
    require_date(value)
    if type(days) is not int:
        raise ConventionError("Business-day offset must be an integer")
    direction = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining:
        value = _step(value, direction)
        if calendar.is_business_day(value):
            remaining -= 1
    return value


def year_fraction(start: date, end: date, convention: DayCount) -> float:
    """Signed accrual on [start, end); reverse dates negate the result.

    ACT/ACT ISDA partitions by calendar year; 30E/360 clips both days to 30.
    No business-day adjustment or schedule inference is performed here.
    """
    require_date(start)
    require_date(end)
    if not isinstance(convention, DayCount):
        raise ConventionError("Unsupported day-count convention")
    if end < start:
        return -year_fraction(end, start, convention)
    actual_days = (end - start).days
    if convention == DayCount.ACT_360:
        return actual_days / 360.0
    if convention == DayCount.ACT_365_FIXED:
        return actual_days / 365.0
    if convention == DayCount.THIRTY_E_360:
        return (
            360 * (end.year - start.year)
            + 30 * (end.month - start.month)
            + min(end.day, 30)
            - min(start.day, 30)
        ) / 360.0
    total = 0.0
    cursor = start
    while cursor < end:
        boundary = date(cursor.year + 1, 1, 1) if cursor.year < end.year else end
        segment_end = min(boundary, end)
        denominator = 366.0 if year_calendar.isleap(cursor.year) else 365.0
        total += (segment_end - cursor).days / denominator
        cursor = segment_end
    return total


def validate_date_grid(values: Iterable[date]) -> tuple[date, ...]:
    """Freeze a nonempty, strictly increasing grid of civil dates."""
    result = tuple(require_date(value) for value in values)
    if not result or any(right <= left for left, right in zip(result, result[1:], strict=False)):
        raise ConventionError("Date grid must be nonempty and strictly increasing")
    return result
