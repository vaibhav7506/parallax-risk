"""Explicit conditional-rate/FX scenario construction; future fixings remain path-owned."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import (
    CurveId,
    MarketSnapshotId,
    MarketSnapshotVersion,
    QuoteId,
)
from parallax_risk.common.time import require_date, year_fraction
from parallax_risk.domain._validation import require_currency, require_token, require_tuple
from parallax_risk.domain.instruments.cashflows import FloatingRateCashFlow
from parallax_risk.domain.instruments.rates.contracts import InterestRateSwap
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import CurveSet, DiscountCurve, ForwardCurve
from parallax_risk.domain.market.observations import (
    FxSpot,
    Quote,
    QuoteUnit,
    RateFixing,
    SourceMetadata,
)
from parallax_risk.domain.market.snapshot import MarketSnapshot
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.rates import HullWhite, Vasicek
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.pricing.engine import PricingContext
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.contracts import PathBatch, ProcessComponent, SimulationRequest


@dataclass(frozen=True, slots=True)
class RateBinding:
    """One Q short-rate state to a currency discount curve and declared same-curve indices."""

    currency: Currency
    component: str
    projection_indices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_currency(self.currency)
        require_token(self.component)
        require_tuple(self.projection_indices, str)
        for index in self.projection_indices:
            require_token(index)
        if len(set(self.projection_indices)) != len(self.projection_indices):
            raise DomainValidationError("Projection index bindings must be unique")


@dataclass(frozen=True, slots=True)
class FxBinding:
    """Explicit today's QUOTE/BASE simulated GBM spot; no inferred settlement lag/basis."""

    base: Currency
    quote: Currency
    component: str

    def __post_init__(self) -> None:
        require_currency(self.base)
        require_currency(self.quote)
        require_token(self.component)
        if self.base == self.quote:
            raise DomainValidationError("FX binding currencies must differ")


def component(request: SimulationRequest, name: str) -> tuple[ProcessComponent, int]:
    """Resolve exact component/state offset; no positional guesses or first-factor fallback."""
    offset = 0
    for item in request.components:
        if item.name == name:
            return item, offset
        offset += item.process.state_dimension
    raise DomainValidationError("Requested scenario component is absent")


@dataclass(frozen=True, slots=True)
class ConditionalMarketScenario:
    """Model-derived future markets, exact at supplied cash-flow knots.

    Vasicek/HullWhite conditional bonds provide discounts; LOG_LINEAR interpolation
    between caller knots and ERROR extrapolation are explicit. Simulated fixings
    are generated once at their exact grid date and retained without lookahead.
    Single-curve projection is a declared assumption, not inferred market data.
    """

    request: SimulationRequest
    dates: tuple[date, ...]
    knot_dates: tuple[date, ...]
    rates: tuple[RateBinding, ...]
    fx: tuple[FxBinding, ...] = ()
    initial_fixings: tuple[RateFixing, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, SimulationRequest):
            raise DomainValidationError("Conditional market requires simulation configuration")
        require_tuple(self.dates, date, nonempty=True)
        require_tuple(self.knot_dates, date, nonempty=True)
        for value in (*self.dates, *self.knot_dates):
            require_date(value)
        if len(self.dates) != len(self.request.grid.times) or any(
            b <= a for a, b in zip(self.dates, self.dates[1:], strict=False)
        ):
            raise DomainValidationError("Scenario dates must increase and align with time grid")
        times = tuple(year_fraction(self.dates[0], d, DayCount.ACT_365_FIXED) for d in self.dates)
        if times != self.request.grid.times:
            raise DomainValidationError(
                "Scenario grid must equal ACT/365F date fractions from origin"
            )
        if (
            any(b <= a for a, b in zip(self.knot_dates, self.knot_dates[1:], strict=False))
            or self.knot_dates[-1] <= self.dates[-1]
        ):
            raise DomainValidationError(
                "Curve knots must increase and cover beyond scenario horizon"
            )
        require_tuple(self.rates, RateBinding, nonempty=True)
        require_tuple(self.fx, FxBinding)
        require_tuple(self.initial_fixings, RateFixing)
        if len({b.currency for b in self.rates}) != len(self.rates):
            raise DomainValidationError("One rate binding per currency is required")
        currencies = {b.currency for b in self.rates}
        for binding in self.rates:
            item, _ = component(self.request, binding.component)
            if (
                not isinstance(item.process, (Vasicek, HullWhite))
                or item.measure != "Q"
                or item.state_units != ("decimal_annual_rate",)
            ):
                raise DomainValidationError(
                    "Rate binding requires a Q short-rate component with rate units"
                )
        pairs = {(b.base, b.quote) for b in self.fx}
        if len(pairs) != len(self.fx) or any((q, b) in pairs for b, q in pairs):
            raise DomainValidationError("FX orientations must be unique without inverse duplicates")
        for fx_binding in self.fx:
            item, _ = component(self.request, fx_binding.component)
            if (
                not isinstance(item.process, GeometricBrownianMotion)
                or item.measure != "Q"
                or item.state_units != (f"{fx_binding.quote}/{fx_binding.base}",)
                or not {fx_binding.base, fx_binding.quote} <= currencies
            ):
                raise DomainValidationError(
                    "FX binding requires Q GBM, declared pair units and currency curves"
                )
        if any(
            f.fixing_date > self.dates[0]
            or f.source.observed_at.date() > self.dates[0]
            or f.currency not in currencies
            for f in self.initial_fixings
        ):
            raise DomainValidationError(
                "Initial fixings must be known at origin in bound currencies"
            )
        if len({(f.currency, f.index, f.fixing_date) for f in self.initial_fixings}) != len(
            self.initial_fixings
        ):
            raise DomainValidationError("Duplicate initial fixing")

    @property
    def hash(self) -> str:
        return content_hash(self)

    def path(
        self, book: PortfolioSnapshot, batch: PathBatch, local_path: int
    ) -> Iterator[PricingContext]:
        """Create markets using only the state/fixings known at each supplied civil date."""
        integer(local_path, "local path", minimum=0, maximum=batch.path_count - 1)
        if batch.values.shape[1:] != (len(self.dates), self.request.state_dimension):
            raise DomainValidationError("Scenario batch shape does not match its request")
        fixings = list(self.initial_fixings)
        keys = {(f.currency, f.index, f.fixing_date) for f in fixings}
        coupons: list[FloatingRateCashFlow] = []
        for cp in book.counterparties:
            for scope in cp.netting_sets:
                for trade in scope.trades:
                    if not trade.active(book.as_of):
                        continue
                    instrument = trade.instrument
                    if isinstance(instrument, FloatingRateCashFlow):
                        coupons.append(instrument)
                    if isinstance(instrument, InterestRateSwap):
                        coupons.extend(
                            FloatingRateCashFlow(
                                instrument.notional,
                                p,
                                d,
                                instrument.index,
                                instrument.floating_day_count,
                                instrument.floating_spread,
                                instrument.floating_gearing,
                            )
                            for p, d in zip(
                                instrument.floating_periods, instrument.fixing_dates, strict=True
                            )
                        )
        fixing_specs: dict[tuple[Currency, str, date], tuple[date, date, DayCount]] = {}
        for coupon in coupons:
            key = (coupon.notional.currency, coupon.index, coupon.fixing_date)
            spec = (coupon.period.start, coupon.period.end, coupon.day_count)
            if key in fixing_specs and fixing_specs[key] != spec:
                raise DomainValidationError(
                    "Same index fixing cannot have conflicting tenor/day-count specs"
                )
            fixing_specs[key] = spec
            if (
                self.dates[0] < coupon.fixing_date <= self.dates[-1]
                and coupon.fixing_date not in self.dates
            ):
                raise DomainValidationError(
                    "Every future fixing within horizon must be on scenario grid"
                )
        for step, as_of in enumerate(self.dates):
            source = SourceMetadata(
                "model-derived-scenario",
                "Synthetic scenario; not observed market data",
                datetime.combine(as_of, datetime.min.time(), UTC),
                True,
            )
            curves: list[DiscountCurve] = []
            forwards: list[ForwardCurve] = []
            quotes: list[Quote] = []
            for binding in self.rates:
                item, offset = component(self.request, binding.component)
                process = item.process
                assert isinstance(process, (Vasicek, HullWhite))
                rate = float(batch.values.array[local_path, step, offset])
                t = self.request.grid.times[step]
                knots = (as_of, *(d for d in self.knot_dates if d > as_of))
                discounts = tuple(
                    process.bond(rate, year_fraction(as_of, d, DayCount.ACT_365_FIXED))
                    if isinstance(process, Vasicek)
                    else process.bond(
                        t, year_fraction(self.dates[0], d, DayCount.ACT_365_FIXED), rate
                    )
                    for d in knots
                )
                curve = DiscountCurve(
                    CurveId(f"{binding.currency}-conditional"),
                    binding.currency,
                    as_of,
                    DayCount.ACT_365_FIXED,
                    tuple(year_fraction(as_of, d, DayCount.ACT_365_FIXED) for d in knots),
                    discounts,
                    InterpolationKind.LOG_LINEAR,
                    ExtrapolationPolicy.ERROR,
                )
                curves.append(curve)
                forwards.extend(ForwardCurve(i, curve) for i in binding.projection_indices)
                quotes.append(
                    Quote(
                        QuoteId(f"{binding.currency}-scenario-rate"),
                        binding.currency,
                        rate,
                        QuoteUnit.DECIMAL_ANNUAL_RATE,
                        source,
                    )
                )
            curve_set = CurveSet(tuple(curves), tuple(forwards))
            for key, spec in fixing_specs.items():
                currency, index, fixing_date = key
                if fixing_date == as_of and fixing_date > self.dates[0] and key not in keys:
                    start, end, day_count = spec
                    rate = curve_set.forward_curve(currency, index).simple_rate(
                        start, end, day_count
                    )
                    fixings.append(
                        RateFixing(
                            QuoteId(f"fix-{currency}-{index}-{fixing_date.isoformat()}"),
                            currency,
                            index,
                            fixing_date,
                            rate,
                            source,
                        )
                    )
                    keys.add(key)
            spots = []
            for fx_binding in self.fx:
                _, offset = component(self.request, fx_binding.component)
                spots.append(
                    FxSpot(
                        QuoteId(f"{fx_binding.base}-{fx_binding.quote}-scenario"),
                        fx_binding.base,
                        fx_binding.quote,
                        as_of,
                        float(batch.values.array[local_path, step, offset]),
                        source,
                    )
                )
            snapshot = MarketSnapshot(
                MarketSnapshotId(f"scenario-{batch.start_path + local_path}"),
                MarketSnapshotVersion(as_of.isoformat()),
                as_of,
                tuple(b.currency for b in self.rates),
                quotes=tuple(quotes),
                fx_spots=tuple(spots),
                fixings=tuple(fixings),
            )
            yield PricingContext(snapshot, curve_set)
