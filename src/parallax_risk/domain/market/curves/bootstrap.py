"""Sequential single-curve bootstrap, with bounded bisection and quote diagnostics."""

import math
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import CurveBootstrapError, CurveError, NumericalError
from parallax_risk.common.identifiers import CurveId, QuoteId
from parallax_risk.common.math import NumericalTolerance, require_finite
from parallax_risk.common.time import require_date, validate_date_grid
from parallax_risk.domain._validation import positive_accrual, require_currency
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import DiscountCurve


class BootstrapQuote(Protocol):
    """A currency quote with a final cash-flow date and deterministic repricing rule."""

    @property
    def quote_id(self) -> QuoteId:
        """Observation identity."""
        ...

    @property
    def currency(self) -> Currency:
        """Quote currency."""
        ...

    @property
    def maturity(self) -> date:
        """Final curve node date."""
        ...

    @property
    def rate(self) -> float:
        """Observed decimal annual quote."""
        ...

    def model_rate(self, curve: DiscountCurve) -> float:
        """Reprice the quote under a candidate discount curve."""
        ...


def _quote_contract(
    quote_id: QuoteId, currency: Currency, rate: float, day_count: DayCount
) -> None:
    if not isinstance(quote_id, QuoteId) or not isinstance(day_count, DayCount):
        raise CurveError("Bootstrap quote identity and day count must be explicit")
    require_currency(currency)
    require_finite(rate, name="bootstrap quote rate")


@dataclass(frozen=True, slots=True)
class DepositQuote:
    """Simple deposit beginning on curve valuation date, without a spot settlement lag."""

    quote_id: QuoteId
    currency: Currency
    maturity: date
    rate: float
    day_count: DayCount

    def __post_init__(self) -> None:
        _quote_contract(self.quote_id, self.currency, self.rate, self.day_count)
        require_date(self.maturity)
        object.__setattr__(self, "rate", float(self.rate))

    def model_rate(self, curve: DiscountCurve) -> float:
        """Return (1/D(T)-1)/accrual, with currency and positive-time checks."""
        if curve.currency != self.currency:
            raise CurveError("Deposit quote currency differs from curve")
        accrual = positive_accrual(curve.valuation_date, self.maturity, self.day_count)
        return require_finite(
            (1.0 / curve.discount(self.maturity) - 1.0) / accrual, name="deposit model rate"
        )


@dataclass(frozen=True, slots=True)
class ParSwapQuote:
    """Single-curve par swap starting at valuation date, payments at accrual ends.

    Floating spread is zero, notional is constant, and no payment/settlement lag
    is assumed. These quote conventions differ from a general dual-curve swap.
    """

    quote_id: QuoteId
    currency: Currency
    payment_dates: tuple[date, ...]
    rate: float
    fixed_day_count: DayCount

    def __post_init__(self) -> None:
        _quote_contract(self.quote_id, self.currency, self.rate, self.fixed_day_count)
        if not isinstance(self.payment_dates, tuple):
            raise CurveError("Bootstrap payment dates must be immutable")
        validate_date_grid(self.payment_dates)
        object.__setattr__(self, "rate", float(self.rate))

    @property
    def maturity(self) -> date:
        """Final fixed-leg payment date."""
        return self.payment_dates[-1]

    def model_rate(self, curve: DiscountCurve) -> float:
        """Return (1-D(T))/sum(alpha_i*D(T_i)) under the documented single-curve model."""
        if curve.currency != self.currency:
            raise CurveError("Par swap quote currency differs from curve")
        starts = (curve.valuation_date, *self.payment_dates[:-1])
        contributions = tuple(
            require_finite(
                positive_accrual(start, end, self.fixed_day_count) * curve.discount(end),
                name="par swap annuity contribution",
            )
            for start, end in zip(starts, self.payment_dates, strict=True)
        )
        try:
            annuity = require_finite(math.fsum(contributions), name="par swap annuity")
        except OverflowError:
            raise NumericalError("Par swap annuity overflowed") from None
        if annuity <= 0:
            raise CurveError("Par swap annuity must be strictly positive")
        return require_finite(
            (1.0 - curve.discount(self.maturity)) / annuity, name="par swap model rate"
        )


@dataclass(frozen=True, slots=True)
class BootstrapSettings:
    """Positive DF bracket, decimal-rate residual gate and DF root tolerance.

    The generous default DF bracket is a numerical domain, not a plausibility
    or regulatory limit. Bounds and tolerances are recorded in the result.
    """

    minimum_discount: float = 1e-8
    maximum_discount: float = 10.0
    rate_residual_tolerance: float = 1e-12
    discount_tolerance: NumericalTolerance = NumericalTolerance(1e-13, 1e-12)
    maximum_iterations: int = 200

    def __post_init__(self) -> None:
        for name in ("minimum_discount", "maximum_discount", "rate_residual_tolerance"):
            require_finite(getattr(self, name), name=name)
        if (
            not 0 < self.minimum_discount < self.maximum_discount
            or self.rate_residual_tolerance <= 0
        ):
            raise CurveError(
                "Bootstrap bracket must be positive/increasing and residual tolerance positive"
            )
        if not isinstance(self.discount_tolerance, NumericalTolerance):
            raise CurveError("Bootstrap discount tolerance must be explicitly typed")
        if type(self.maximum_iterations) is not int or self.maximum_iterations <= 0:
            raise CurveError("Bootstrap iteration limit must be a positive integer")


@dataclass(frozen=True, slots=True)
class BootstrapDiagnostic:
    """Actual observed/repriced annual rates, signed residual and root iteration count."""

    quote_id: QuoteId
    observed_rate: float
    model_rate: float
    residual: float
    iterations: int


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """All-or-nothing curve construction with reproducible input/configuration digests."""

    curve: DiscountCurve
    diagnostics: tuple[BootstrapDiagnostic, ...]
    input_hash: str
    settings: BootstrapSettings


def bootstrap_discount_curve(
    quotes: tuple[BootstrapQuote, ...],
    *,
    curve_id: CurveId,
    currency: Currency,
    valuation_date: date,
    curve_day_count: DayCount,
    interpolation: InterpolationKind,
    extrapolation: ExtrapolationPolicy,
    settings: BootstrapSettings | None = None,
) -> BootstrapResult:
    """Sequentially solve positive DF nodes and verify every quote on the final curve.

    Quote maturities must be supplied in strictly increasing order; no sorting,
    missing-node substitution or invalid-matrix repair is performed. A failed
    bracket/convergence/repricing gate raises instead of returning a partial curve.
    """
    require_date(valuation_date)
    require_currency(currency)
    settings = BootstrapSettings() if settings is None else settings
    if not isinstance(settings, BootstrapSettings):
        raise CurveError("Bootstrap settings must be typed")
    if (
        not isinstance(quotes, tuple)
        or not quotes
        or any(not isinstance(item, (DepositQuote, ParSwapQuote)) for item in quotes)
    ):
        raise CurveError("Phase 2 bootstrap requires immutable deposit/par-swap quote tuples")
    if len({quote.quote_id for quote in quotes}) != len(quotes):
        raise CurveError("Bootstrap quote IDs must be unique")
    maturities = validate_date_grid(tuple(quote.maturity for quote in quotes))
    if maturities[0] <= valuation_date or any(quote.currency != currency for quote in quotes):
        raise CurveError("Bootstrap quotes must have future maturities in the declared currency")
    times: tuple[float, ...] = (0.0,)
    discounts: tuple[float, ...] = (1.0,)
    iteration_counts = []
    for quote in quotes:
        node_time = positive_accrual(valuation_date, quote.maturity, curve_day_count)

        def residual(
            discount: float,
            current_quote: BootstrapQuote = quote,
            current_time: float = node_time,
            previous_times: tuple[float, ...] = times,
            previous_discounts: tuple[float, ...] = discounts,
        ) -> float:
            candidate = DiscountCurve(
                curve_id,
                currency,
                valuation_date,
                curve_day_count,
                (*previous_times, current_time),
                (*previous_discounts, discount),
                interpolation,
                extrapolation,
            )

            return require_finite(
                current_quote.model_rate(candidate) - current_quote.rate, name="bootstrap residual"
            )

        low, high = settings.minimum_discount, settings.maximum_discount
        low_value, high_value = residual(low), residual(high)
        iterations = 0
        if abs(low_value) <= settings.rate_residual_tolerance:
            root = low
        elif abs(high_value) <= settings.rate_residual_tolerance:
            root = high
        else:
            if (low_value > 0) == (high_value > 0):
                raise CurveBootstrapError(
                    "Bootstrap root is not bracketed within declared positive DF bounds"
                )
            for iteration in range(1, settings.maximum_iterations + 1):
                iterations = iteration
                root = low + (high - low) / 2.0
                value = residual(root)
                if abs(
                    value
                ) <= settings.rate_residual_tolerance and settings.discount_tolerance.is_close(
                    low, high
                ):
                    break
                if root in (low, high):
                    raise CurveBootstrapError(
                        "Bootstrap stagnated before satisfying quote and discount convergence gates"
                    )
                if (value > 0) == (low_value > 0):
                    low, low_value = root, value
                else:
                    high = root
            else:
                raise CurveBootstrapError("Bootstrap exceeded its declared iteration limit")
        times, discounts = (*times, node_time), (*discounts, root)
        iteration_counts.append(iterations)
    curve = DiscountCurve(
        curve_id,
        currency,
        valuation_date,
        curve_day_count,
        times,
        discounts,
        interpolation,
        extrapolation,
    )
    diagnostics = tuple(
        BootstrapDiagnostic(
            quote.quote_id,
            quote.rate,
            quote.model_rate(curve),
            quote.model_rate(curve) - quote.rate,
            iterations,
        )
        for quote, iterations in zip(quotes, iteration_counts, strict=True)
    )
    if any(abs(item.residual) > settings.rate_residual_tolerance for item in diagnostics):
        raise CurveBootstrapError("Final curve failed all-quote repricing gate")
    return BootstrapResult(curve, diagnostics, content_hash(quotes), settings)
