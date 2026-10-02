import math
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from parallax_risk.common.enums import Compounding, Currency, DayCount
from parallax_risk.common.errors import (
    CurveBootstrapError,
    CurveError,
    DomainValidationError,
    MissingMarketDataError,
    NumericalError,
)
from parallax_risk.common.identifiers import CurveId, QuoteId
from parallax_risk.domain.market.curves.bootstrap import (
    BootstrapSettings,
    DepositQuote,
    ParSwapQuote,
    bootstrap_discount_curve,
)
from parallax_risk.domain.market.curves.diagnostics import diagnose_curve
from parallax_risk.domain.market.curves.interpolation import (
    ExtrapolationPolicy,
    InterpolationKind,
    LinearInterpolator,
    LogLinearInterpolator,
    interpolator,
)
from parallax_risk.domain.market.curves.term_structures import (
    CurveSet,
    ForwardCurve,
    ZeroCurve,
    curve_time,
)
from tests.fixtures.deterministic import INDEX, VALUATION, YEAR_ONE, YEAR_TWO, flat_curve


def bootstrap(quotes, **overrides):
    kwargs = {
        "curve_id": CurveId("boot"),
        "currency": Currency.USD,
        "valuation_date": VALUATION,
        "curve_day_count": DayCount.ACT_365_FIXED,
        "interpolation": InterpolationKind.LOG_LINEAR,
        "extrapolation": ExtrapolationPolicy.ERROR,
    }
    kwargs.update(overrides)
    return bootstrap_discount_curve(quotes, **kwargs)


def deposit(maturity=YEAR_ONE, rate=0.05, quote_id="deposit"):
    return DepositQuote(QuoteId(quote_id), Currency.USD, maturity, rate, DayCount.ACT_365_FIXED)


def par_quote(rate=0.05, quote_id="swap"):
    return ParSwapQuote(
        QuoteId(quote_id), Currency.USD, (YEAR_ONE, YEAR_TWO), rate, DayCount.ACT_365_FIXED
    )


def test_interpolation_formula_benchmarks_and_exact_knots():
    x, y = (0.0, 1.0, 2.0), (1.0, 0.8, 0.64)
    assert LinearInterpolator().interpolate(0.5, x, y) == 0.9
    assert LogLinearInterpolator().interpolate(0.5, x, y) == pytest.approx(
        math.sqrt(0.8), abs=1e-14
    )
    for strategy in (LinearInterpolator(), LogLinearInterpolator()):
        for point, expected in zip(x, y, strict=True):
            assert strategy.interpolate(point, x, y) == expected
        assert strategy.interpolate(0, (0,), (3,)) == 3
    with pytest.raises(CurveError):
        interpolator("linear")


@pytest.mark.parametrize(
    "x,y,point",
    [
        ((), (), 0),
        ([0, 1], (1, 2), 0.5),
        ((0, 1), [1, 2], 0.5),
        ((0, 1), (1,), 0.5),
        ((0, 0), (1, 2), 0),
        ((1, 0), (1, 2), 0.5),
        ((0, 1), (1, 2), -1),
        ((0, 1), (1, 2), 2),
    ],
)
def test_interpolation_rejects_invalid_nodes_and_implicit_extrapolation(x, y, point):
    with pytest.raises(CurveError):
        LinearInterpolator().interpolate(point, x, y)


def test_loglinear_nonpositive_and_nonfinite_nodes():
    for values in ((1.0, 0.0), (1.0, -1.0)):
        with pytest.raises(CurveError):
            LogLinearInterpolator().interpolate(0.5, (0, 1), values)
    with pytest.raises(NumericalError):
        LinearInterpolator().interpolate(0.5, (0, 1), (1, float("nan")))


def test_discount_curve_anchor_dates_extrapolation_and_hash():
    curve = flat_curve()
    assert curve.discount(0) == 1
    assert curve.discount(YEAR_ONE) == math.exp(-0.05)
    assert curve.discount(0.5) == pytest.approx(math.exp(-0.025), rel=1e-12)
    assert curve.continuous_zero_rate(YEAR_TWO) == pytest.approx(0.05, rel=1e-12)
    assert replace(curve, interpolation=InterpolationKind.LINEAR).discount(0.5) == pytest.approx(
        (1 + math.exp(-0.05)) / 2, abs=1e-14
    )
    with pytest.raises(FrozenInstanceError):
        curve.times = (0, 3)
    with pytest.raises(CurveError, match="extrapolation"):
        curve.discount(3)
    extrapolated = replace(curve, extrapolation=ExtrapolationPolicy.FLAT_ZERO)
    assert extrapolated.discount(3) == pytest.approx(math.exp(-0.15), rel=1e-12)
    assert extrapolated.curve_hash != curve.curve_hash
    assert curve.bumped(0.01).discount(0.5) == pytest.approx(math.exp(-0.03), rel=1e-12)
    assert curve.bumped(0).curve_hash == curve.curve_hash


@pytest.mark.parametrize(
    "updates",
    [
        {"curve_id": "x"},
        {"currency": "USD"},
        {"valuation_date": datetime(2025, 1, 1)},
        {"day_count": "ACT/365F"},
        {"extrapolation": "error"},
        {"interpolation": "linear"},
        {"times": (1, 2, 3)},
        {"times": (0,), "discount_factors": (1,)},
        {"discount_factors": (2, 0.9, 0.8)},
        {"discount_factors": (1, 0, 0.8)},
        {"discount_factors": (1, -0.9, 0.8)},
        {"discount_factors": [1, 0.9, 0.8]},
    ],
)
def test_discount_curve_rejects_invalid_contract(updates):
    with pytest.raises(DomainValidationError):
        replace(flat_curve(), **updates)


def test_curve_queries_reject_past_or_undefined_time():
    curve = flat_curve()
    for value in (-1, date(2024, 12, 31), datetime(2025, 1, 1)):
        with pytest.raises(DomainValidationError):
            curve.discount(value)
    with pytest.raises(CurveError):
        curve.continuous_zero_rate(0)
    with pytest.raises(NumericalError):
        curve_time(float("inf"), VALUATION, DayCount.ACT_365_FIXED)


def test_curves_fail_explicitly_on_extreme_extrapolation_and_bumps():
    exploding = replace(
        flat_curve(), discount_factors=(1, 2, 3), extrapolation=ExtrapolationPolicy.FLAT_ZERO
    )
    decaying = replace(flat_curve(), extrapolation=ExtrapolationPolicy.FLAT_ZERO)
    with pytest.raises(NumericalError, match="overflow"):
        exploding.discount(1e6)
    with pytest.raises(NumericalError, match="underflow"):
        decaying.discount(1e6)
    with pytest.raises(NumericalError, match="overflow"):
        decaying.bumped(-1e6)
    with pytest.raises(NumericalError, match="underflow"):
        decaying.bumped(1e6)


@pytest.mark.parametrize(
    "compounding,frequency,expected",
    [
        (Compounding.SIMPLE, None, 1 / 1.1),
        (Compounding.CONTINUOUS, None, math.exp(-0.1)),
        (Compounding.PERIODIC, 2, 1 / (1.025**4)),
    ],
)
def test_zero_curve_declared_compounding(compounding, frequency, expected):
    curve = ZeroCurve(
        CurveId("zero"),
        Currency.USD,
        VALUATION,
        DayCount.ACT_365_FIXED,
        (0, 1, 2),
        (0.05, 0.05, 0.05),
        compounding,
        ExtrapolationPolicy.ERROR,
        frequency,
    )
    assert curve.discount(YEAR_TWO) == pytest.approx(expected, rel=1e-12)
    assert curve.zero_rate(0.5) == 0.05
    sampled = curve.to_discount_curve(
        interpolation=InterpolationKind.LOG_LINEAR, extrapolation=ExtrapolationPolicy.ERROR
    )
    assert sampled.discount(YEAR_TWO) == curve.discount(YEAR_TWO)
    assert sampled.discount(0) == 1
    with pytest.raises(CurveError):
        curve.zero_rate(3)
    extrapolated = replace(curve, extrapolation=ExtrapolationPolicy.FLAT_ZERO)
    assert extrapolated.zero_rate(3) == 0.05


def test_zero_rate_interpolation_differs_from_log_discount_sampling():
    curve = ZeroCurve(
        CurveId("zero"),
        Currency.USD,
        VALUATION,
        DayCount.ACT_365_FIXED,
        (0, 1, 2),
        (0.02, 0.04, 0.08),
        Compounding.CONTINUOUS,
        ExtrapolationPolicy.ERROR,
    )
    assert curve.zero_rate(1.5) == 0.06
    sampled = curve.to_discount_curve(
        interpolation=InterpolationKind.LOG_LINEAR, extrapolation=ExtrapolationPolicy.ERROR
    )
    assert curve.discount(1.5) == pytest.approx(math.exp(-0.09), rel=1e-12)
    assert sampled.discount(1.5) == pytest.approx(math.exp(-0.10), rel=1e-12)


def test_forward_curve_and_curve_set_assignment_contracts():
    discount = flat_curve()
    projection = flat_curve(rate=0.03, curve_id="projection")
    forward = ForwardCurve(INDEX, projection)
    assert forward.simple_rate(YEAR_ONE, YEAR_TWO, DayCount.ACT_365_FIXED) == pytest.approx(
        math.expm1(0.03), abs=1e-14
    )
    curves = CurveSet((discount,), (forward,))
    assert curves.discount_curve(Currency.USD) is discount
    assert curves.forward_curve(Currency.USD, INDEX) is forward
    bumped = curves.bumped((projection.curve_id,), 0.01)
    assert bumped.discount_curves == curves.discount_curves
    assert bumped.forward_curve(Currency.USD, INDEX).simple_rate(
        YEAR_ONE, YEAR_TWO, DayCount.ACT_365_FIXED
    ) == pytest.approx(math.expm1(0.04), abs=1e-14)
    assert curves.curve_hash != bumped.curve_hash
    shared = CurveSet((discount,), (ForwardCurve(INDEX, discount),))
    shifted = shared.bumped((discount.curve_id,), 0.01)
    assert shifted.discount_curves[0] == shifted.forward_curves[0].curve
    for action in (
        lambda: curves.discount_curve(Currency.EUR),
        lambda: curves.forward_curve(Currency.USD, "missing"),
    ):
        with pytest.raises(MissingMarketDataError):
            action()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ForwardCurve(INDEX, "bad"),
        lambda: CurveSet(()),
        lambda: CurveSet([flat_curve()]),
        lambda: CurveSet((flat_curve(), flat_curve(curve_id="other"))),
        lambda: CurveSet(
            (flat_curve(),), (ForwardCurve(INDEX, flat_curve()), ForwardCurve(INDEX, flat_curve()))
        ),
        lambda: CurveSet(
            (flat_curve(), replace(flat_curve(Currency.EUR), valuation_date=YEAR_ONE))
        ),
        lambda: CurveSet((flat_curve(),), (ForwardCurve(INDEX, flat_curve(rate=0.03)),)),
    ],
)
def test_curve_set_rejects_ambiguity_and_mutability(factory):
    with pytest.raises(DomainValidationError):
        factory()


def test_curve_bump_scope_rejects_invalid_ids():
    curves = CurveSet((flat_curve(),))
    for ids in (
        (),
        (CurveId("missing"),),
        (flat_curve().curve_id, flat_curve().curve_id),
        ("USD-discount",),
    ):
        with pytest.raises(DomainValidationError):
            curves.bumped(ids, 0.01)


def test_curve_diagnostics_does_not_misclassify_negative_rates():
    positive = diagnose_curve(flat_curve())
    negative = diagnose_curve(flat_curve(rate=-0.01))
    assert positive.nonincreasing_discounts and positive.increasing_intervals == ()
    assert not negative.nonincreasing_discounts and negative.increasing_intervals == (0, 1)
    assert negative.continuous_zero_rates == pytest.approx((-0.01, -0.01), abs=1e-14)
    assert negative.minimum_discount == 1
    assert positive.node_count == 3


def test_deposit_and_par_swap_bootstrap_hand_derived_benchmark():
    result = bootstrap((deposit(), par_quote()))
    assert result.curve.discount_factors == pytest.approx((1, 1 / 1.05, 1 / 1.05**2), abs=1e-12)
    assert all(
        abs(item.residual) <= result.settings.rate_residual_tolerance for item in result.diagnostics
    )
    assert all(item.iterations > 0 for item in result.diagnostics)
    assert len(result.input_hash) == 64
    assert bootstrap((deposit(), par_quote())) == result
    changed = bootstrap((deposit(rate=0.06), par_quote()))
    assert changed.input_hash != result.input_hash


def test_bootstrap_interpolated_coupon_dates_and_short_deposits():
    truth = flat_curve()
    payments = (date(2026, 7, 2), YEAR_TWO)
    model_quote = ParSwapQuote(QuoteId("swap"), Currency.USD, payments, 0, DayCount.ACT_365_FIXED)
    quoted = replace(model_quote, rate=model_quote.model_rate(truth))
    deposit_rate = math.exp(0.05) - 1
    result = bootstrap((deposit(rate=deposit_rate), quoted))
    assert result.curve.discount(YEAR_TWO) == pytest.approx(math.exp(-0.1), abs=2e-12)
    # A one-day deposit needs more DF digits than a yearly quote for the same rate residual gate.
    short = bootstrap((deposit(date(2025, 1, 2), 0.05),))
    assert abs(short.diagnostics[0].residual) <= short.settings.rate_residual_tolerance
    assert short.curve.discount(date(2025, 1, 2)) == pytest.approx(1 / (1 + 0.05 / 365), abs=1e-14)


def test_bootstrap_negative_rates_and_endpoint_roots():
    result = bootstrap((deposit(rate=-0.01),))
    assert result.curve.discount(YEAR_ONE) > 1
    bounds = BootstrapSettings(minimum_discount=0.5, maximum_discount=2)
    low = bootstrap((deposit(rate=1),), settings=bounds)
    high = bootstrap((deposit(rate=-0.5),), settings=bounds)
    assert low.curve.discount(YEAR_ONE) == 0.5 and low.diagnostics[0].iterations == 0
    assert high.curve.discount(YEAR_ONE) == 2 and high.diagnostics[0].iterations == 0


@pytest.mark.parametrize(
    "quotes,overrides",
    [
        ((), {}),
        ([deposit()], {}),
        ((object(),), {}),
        ((deposit(), deposit()), {}),
        ((par_quote(), deposit()), {}),
        ((deposit(VALUATION),), {}),
        ((replace(deposit(), currency=Currency.EUR),), {}),
        ((deposit(),), {"settings": "bad"}),
    ],
)
def test_bootstrap_rejects_missing_unordered_or_inconsistent_quotes(quotes, overrides):
    with pytest.raises(DomainValidationError):
        bootstrap(quotes, **overrides)


def test_bootstrap_failure_is_not_partial_or_silent():
    with pytest.raises(CurveBootstrapError, match="bracketed"):
        bootstrap((deposit(rate=-2),))
    with pytest.raises(CurveBootstrapError, match="iteration limit"):
        bootstrap((deposit(),), settings=BootstrapSettings(maximum_iterations=1))
    with pytest.raises(CurveBootstrapError, match="stagnated"):
        bootstrap(
            (deposit(rate=0.05123456789),),
            settings=BootstrapSettings(rate_residual_tolerance=1e-30),
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"minimum_discount": 0},
        {"maximum_discount": 1e-9},
        {"rate_residual_tolerance": 0},
        {"maximum_iterations": 0},
        {"maximum_iterations": True},
        {"discount_tolerance": 0.001},
        {"minimum_discount": float("nan")},
    ],
)
def test_bootstrap_settings_validate_numerical_contract(updates):
    with pytest.raises((CurveError, NumericalError)):
        replace(BootstrapSettings(), **updates)


def test_bootstrap_quotes_validate_their_own_conventions():
    for action in (
        lambda: replace(deposit(), quote_id="bad"),
        lambda: replace(deposit(), day_count="ACT/365F"),
        lambda: replace(par_quote(), payment_dates=[]),
        lambda: replace(par_quote(), payment_dates=()),
        lambda: deposit().model_rate(flat_curve(Currency.EUR)),
        lambda: par_quote().model_rate(flat_curve(Currency.EUR)),
        lambda: par_quote().model_rate(replace(flat_curve(), valuation_date=YEAR_ONE)),
    ):
        with pytest.raises(DomainValidationError):
            action()
