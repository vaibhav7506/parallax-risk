from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest

from parallax_risk.common.enums import BusinessDayConvention as BDC
from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.errors import (
    ConventionError,
    CurrencyMismatchError,
    DomainValidationError,
    NumericalError,
)
from parallax_risk.common.identifiers import (
    CounterpartyId,
    CsaId,
    ModelId,
    ModelVersion,
    NettingSetId,
    RiskRunId,
    TradeId,
)
from parallax_risk.common.math import NumericalTolerance, accumulation_factor, require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import (
    HolidayCalendar,
    add_business_days,
    adjust_business_day,
    require_date,
    utc_timestamp,
    validate_date_grid,
    year_fraction,
)


@pytest.mark.parametrize(
    "kind", [TradeId, CounterpartyId, NettingSetId, CsaId, ModelId, ModelVersion, RiskRunId]
)
def test_identifiers_nominal_and_frozen(kind):
    value = kind("item-1:version.0")
    assert str(value) == "item-1:version.0"
    assert value == kind(value.value)
    assert len({value, kind(value.value)}) == 1
    with pytest.raises(FrozenInstanceError):
        value.value = "changed"


def test_identifier_nominal_separation():
    assert TradeId("same") != CounterpartyId("same")
    assert ModelId("same") != ModelVersion("same")


@pytest.mark.parametrize("value", ["", " ", " a", "a ", "a/b", "a\n", "ü", "x" * 129, 1])
def test_identifier_rejects_invalid_tokens(value):
    with pytest.raises(DomainValidationError):
        TradeId(value)


def test_money_exact_arithmetic_and_sign():
    a, b = Money(Decimal("0.1"), Currency.USD), Money(Decimal("0.2"), Currency.USD)
    with localcontext() as ambient:
        ambient.prec = 1
        assert (a + b).amount == Decimal("0.3")
        assert (a - b).amount == Decimal("-0.1")
        assert a.scale(Decimal("12.34")).amount == Decimal("1.234")
        negative = -a
        assert -negative == a
        assert (-Money(Decimal("12345.6789"), Currency.USD)).amount == Decimal("-12345.6789")
    with pytest.raises(FrozenInstanceError):
        a.amount = Decimal(1)


@pytest.mark.parametrize("amount", [0.1, 1, "1", Decimal("NaN"), Decimal("Infinity")])
def test_money_rejects_unsafe_amounts(amount):
    with pytest.raises(DomainValidationError):
        Money(amount, Currency.USD)


def test_money_rejects_currency_and_rounding():
    a = Money(Decimal("1"), Currency.USD)
    with pytest.raises(DomainValidationError):
        Money(Decimal(1), "USD")
    with pytest.raises(CurrencyMismatchError):
        a + Money(Decimal(1), Currency.EUR)
    with pytest.raises(DomainValidationError):
        a + 1
    with pytest.raises(DomainValidationError):
        a.scale(float("nan"))
    large = Money(Decimal("1e34"), Currency.USD)
    with pytest.raises(NumericalError):
        large + a
    with pytest.raises(NumericalError):
        Money(Decimal("1." + "2" * 34), Currency.USD).scale(Decimal("1.01"))


def test_timestamps_require_explicit_timezone():
    instant = datetime(2026, 9, 30, 23, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert utc_timestamp(instant) == datetime(2026, 9, 30, 17, 30, tzinfo=UTC)
    with pytest.raises(ConventionError):
        utc_timestamp(datetime(2026, 9, 30))
    with pytest.raises(ConventionError):
        require_date(instant)
    assert require_date(date(2026, 9, 30)) == date(2026, 9, 30)


@pytest.mark.parametrize(
    ("start", "end", "convention", "expected"),
    [
        (date(2024, 1, 1), date(2025, 1, 1), DayCount.ACT_360, 366 / 360),
        (date(2024, 1, 1), date(2025, 1, 1), DayCount.ACT_365_FIXED, 366 / 365),
        (date(2024, 1, 1), date(2025, 1, 1), DayCount.ACT_ACT_ISDA, 1),
        (date(2023, 12, 31), date(2024, 1, 2), DayCount.ACT_ACT_ISDA, 1 / 365 + 1 / 366),
        (date(2024, 1, 31), date(2024, 2, 29), DayCount.THIRTY_E_360, 29 / 360),
        (date(2024, 2, 29), date(2024, 3, 31), DayCount.THIRTY_E_360, 31 / 360),
        (date(9999, 12, 30), date(9999, 12, 31), DayCount.ACT_ACT_ISDA, 1 / 365),
    ],
)
def test_day_count_hand_derived_benchmarks(start, end, convention, expected):
    assert year_fraction(start, end, convention) == pytest.approx(expected, rel=1e-12, abs=1e-14)
    assert year_fraction(end, start, convention) == pytest.approx(-expected, rel=1e-12, abs=1e-14)
    assert year_fraction(start, start, convention) == 0


def test_invalid_day_count_and_grid():
    with pytest.raises(ConventionError):
        year_fraction(date(2024, 1, 1), date(2024, 2, 1), "ACT/360")
    dates = [date(2024, 1, 1), date(2024, 2, 1)]
    assert validate_date_grid(dates) == tuple(dates)
    for bad in ([], dates[::-1], [dates[0], dates[0]], [datetime(2024, 1, 1)]):
        with pytest.raises(ConventionError):
            validate_date_grid(bad)


@pytest.mark.parametrize(
    ("convention", "expected"),
    [
        (BDC.UNADJUSTED, date(2024, 8, 31)),
        (BDC.FOLLOWING, date(2024, 9, 3)),
        (BDC.MODIFIED_FOLLOWING, date(2024, 8, 30)),
        (BDC.PRECEDING, date(2024, 8, 30)),
        (BDC.MODIFIED_PRECEDING, date(2024, 8, 30)),
    ],
)
def test_business_day_conventions_with_explicit_holiday(convention, expected):
    calendar = HolidayCalendar("test-only", holidays=frozenset({date(2024, 9, 2)}))
    assert adjust_business_day(date(2024, 8, 31), calendar, convention) == expected


def test_business_calendar_offsets_and_month_boundary():
    calendar = HolidayCalendar("weekends-only")
    assert adjust_business_day(date(2024, 9, 1), calendar, BDC.MODIFIED_PRECEDING) == date(
        2024, 9, 2
    )
    assert add_business_days(date(2024, 8, 30), 1, calendar) == date(2024, 9, 2)
    assert add_business_days(date(2024, 9, 2), -1, calendar) == date(2024, 8, 30)
    assert add_business_days(date(2024, 9, 1), 0, calendar) == date(2024, 9, 1)
    custom = HolidayCalendar("Friday-weekend", weekend_days=frozenset({4, 5}))
    assert custom.is_business_day(date(2024, 9, 1))
    assert not custom.is_business_day(date(2024, 8, 30))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": ""},
        {"name": 1},
        {"name": "x", "holidays": set()},
        {"name": "x", "weekend_days": set()},
        {"name": "x", "weekend_days": frozenset(range(7))},
        {"name": "x", "weekend_days": frozenset({7})},
        {"name": "x", "weekend_days": frozenset({True})},
        {"name": "x", "holidays": frozenset({datetime(2024, 1, 1)})},
    ],
)
def test_calendar_rejects_invalid_configuration(kwargs):
    with pytest.raises(ConventionError):
        HolidayCalendar(**kwargs)


def test_calendar_bounds_and_invalid_inputs():
    calendar = HolidayCalendar("test")
    for start, offset in ((date.max, 1), (date.min, -1)):
        with pytest.raises(ConventionError):
            add_business_days(start, offset, calendar)
    with pytest.raises(ConventionError):
        add_business_days(date(2026, 9, 30), True, calendar)
    with pytest.raises(ConventionError):
        adjust_business_day(date(2026, 9, 30), calendar, "following")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "1", 10**1000])
def test_nonfinite_or_unsafe_real_rejected(bad):
    with pytest.raises(NumericalError):
        require_finite(bad, name="test")


def test_tolerance_contract():
    tolerance = NumericalTolerance(absolute=1e-12, relative=1e-9)
    assert tolerance.is_close(0, 0.5e-12)
    assert not tolerance.is_close(0, 2e-12)
    assert tolerance.is_close(1000, 1000 + 0.5e-6)
    assert not tolerance.is_close(1000, 1000 + 2e-6)
    with pytest.raises(NumericalError):
        tolerance.is_close(float("nan"), 0)


@pytest.mark.parametrize("absolute,relative", [(-1, 0), (0, -1), (0, 1), (0, 0), (float("inf"), 0)])
def test_invalid_tolerances(absolute, relative):
    with pytest.raises(NumericalError):
        NumericalTolerance(absolute, relative)


@pytest.mark.parametrize(
    "convention,frequency,expected",
    [
        (Compounding.SIMPLE, None, 1.1),
        # exp(0.1), independently evaluated to 50 digits with Decimal.exp.
        (Compounding.CONTINUOUS, None, 1.1051709180756476),
        (Compounding.PERIODIC, 2, 1.025**4),
    ],
)
def test_compounding_formulas(convention, frequency, expected):
    assert accumulation_factor(0.05, 2, convention, periods_per_year=frequency) == pytest.approx(
        expected, rel=1e-12, abs=1e-14
    )
    assert accumulation_factor(0.05, 0, convention, periods_per_year=frequency) == 1


@pytest.mark.parametrize(
    "rate,years,convention,frequency,error",
    [
        (0.1, -1, Compounding.SIMPLE, None, ConventionError),
        (0.1, 1, "simple", None, ConventionError),
        (0.1, 1, Compounding.SIMPLE, 1, ConventionError),
        (0.1, 1, Compounding.PERIODIC, None, ConventionError),
        (0.1, 1, Compounding.PERIODIC, 0, ConventionError),
        (0.1, 1, Compounding.PERIODIC, True, ConventionError),
        (-2, 1, Compounding.PERIODIC, 1, NumericalError),
        (-2, 1, Compounding.SIMPLE, None, NumericalError),
        (1000, 1, Compounding.CONTINUOUS, None, NumericalError),
        (-1000, 1, Compounding.CONTINUOUS, None, NumericalError),
        (1e308, 1e308, Compounding.SIMPLE, None, NumericalError),
    ],
)
def test_compounding_rejects_invalid_domain_and_nonfinite_results(
    rate, years, convention, frequency, error
):
    with pytest.raises(error):
        accumulation_factor(rate, years, convention, periods_per_year=frequency)
