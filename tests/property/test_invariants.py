from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from parallax_risk.common.enums import BusinessDayConvention, Compounding, Currency, DayCount
from parallax_risk.common.math import accumulation_factor
from parallax_risk.common.money import Money
from parallax_risk.common.time import HolidayCalendar, adjust_business_day, year_fraction

DATES = st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
DECIMALS = st.decimals(
    min_value=-1_000_000, max_value=1_000_000, places=4, allow_nan=False, allow_infinity=False
)


@given(DECIMALS, DECIMALS, st.sampled_from(list(Currency)))
def test_money_addition_inverse_and_scaling(a, b, currency):
    left, right = Money(a, currency), Money(b, currency)
    assert left + right == right + left
    assert (left + right) - right == left
    assert left.scale(Decimal(0)) == Money(Decimal(0), currency)
    assert left.scale(Decimal(-1)) == -left


@given(DATES, DATES, st.sampled_from(list(DayCount)))
def test_signed_day_count_symmetry(start, end, convention):
    forward = year_fraction(start, end, convention)
    assert forward == -year_fraction(end, start, convention)
    assert year_fraction(start, start, convention) == 0


@given(DATES, DATES, DATES, st.sampled_from(list(DayCount)))
def test_day_count_interval_additivity(a, b, c, convention):
    first, middle, last = sorted([a, b, c])
    assert year_fraction(first, last, convention) == pytest.approx(
        year_fraction(first, middle, convention) + year_fraction(middle, last, convention),
        rel=1e-12,
        abs=1e-12,
    )


@given(DATES, st.sampled_from(list(BusinessDayConvention)))
def test_calendar_adjustment_idempotence(value, convention):
    calendar = HolidayCalendar("weekends-only-test")
    result = adjust_business_day(value, calendar, convention)
    assert adjust_business_day(result, calendar, convention) == result
    if convention != BusinessDayConvention.UNADJUSTED:
        assert calendar.is_business_day(result)
    if convention in {
        BusinessDayConvention.MODIFIED_FOLLOWING,
        BusinessDayConvention.MODIFIED_PRECEDING,
    }:
        assert result.month == value.month


@given(
    st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=5, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=5, allow_nan=False, allow_infinity=False),
)
def test_continuous_compounding_time_composition(rate, first, second):
    combined = accumulation_factor(rate, first + second, Compounding.CONTINUOUS)
    product = accumulation_factor(rate, first, Compounding.CONTINUOUS) * accumulation_factor(
        rate, second, Compounding.CONTINUOUS
    )
    assert combined == pytest.approx(product, rel=1e-12, abs=1e-12)
