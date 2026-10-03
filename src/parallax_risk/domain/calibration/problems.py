"""Explicit Q-measure synthetic/observed instrument objectives and provenance."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import CalibrationError
from parallax_risk.common.identifiers import QuoteId
from parallax_risk.common.math import require_finite
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain._validation import require_currency, require_tuple
from parallax_risk.domain.market.observations import SourceMetadata
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.base import State, nonnegative, positive, vector
from parallax_risk.domain.models.heston_pricing import FourierSettings, heston_call
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve, Vasicek


def _quote(quote_id: QuoteId, source: SourceMetadata, scale: float) -> None:
    if not isinstance(quote_id, QuoteId) or not isinstance(source, SourceMetadata):
        raise CalibrationError("Calibration quote requires typed identity and provenance")
    positive(scale, "quote residual scale")


@dataclass(frozen=True, slots=True)
class DiscountObservation:
    """Unit-nominal default-free discount bond, maturity in explicit year fractions."""

    quote_id: QuoteId
    maturity: float
    value: float
    source: SourceMetadata
    scale: float = 1.0

    def __post_init__(self) -> None:
        _quote(self.quote_id, self.source, self.scale)
        positive(self.maturity, "discount maturity")
        positive(self.value, "observed discount factor")


@dataclass(frozen=True, slots=True)
class BondOptionObservation:
    """Time-0 European bond call, unit nominal, price/strike in nominal fractions."""

    quote_id: QuoteId
    expiry: float
    maturity: float
    strike: float
    value: float
    source: SourceMetadata
    scale: float = 1.0

    def __post_init__(self) -> None:
        _quote(self.quote_id, self.source, self.scale)
        positive(self.expiry, "bond-option expiry")
        positive(self.strike, "bond-option strike")
        if positive(self.maturity, "bond maturity") <= self.expiry:
            raise CalibrationError("Calibration bond maturity must exceed option expiry")
        nonnegative(self.value, "bond-option observation")


@dataclass(frozen=True, slots=True)
class CallObservation:
    """European call premium in problem currency per one underlying unit."""

    quote_id: QuoteId
    expiry: float
    strike: float
    value: float
    source: SourceMetadata
    scale: float = 1.0

    def __post_init__(self) -> None:
        _quote(self.quote_id, self.source, self.scale)
        positive(self.expiry, "call expiry")
        positive(self.strike, "call strike")
        nonnegative(self.value, "call observation")


type Observation = DiscountObservation | BondOptionObservation | CallObservation


def _dataset[T: Observation](
    currency: Currency, as_of: datetime, observations: tuple[T, ...], kind: type[T]
) -> None:
    require_currency(currency)
    instant = utc_timestamp(as_of)
    require_tuple(observations, kind, nonempty=True)
    ids = tuple(point.quote_id for point in observations)
    if len(set(ids)) != len(ids):
        raise CalibrationError("Calibration quote IDs must be unique")
    if any(point.source.observed_at > instant for point in observations):
        raise CalibrationError("Calibration data cannot be observed after its as-of instant")


class _ProblemValues:
    """Shared immutable objective metadata; no optimizer dependency."""

    __slots__ = ()

    observations: tuple[Observation, ...]

    @property
    def input_hash(self) -> str:
        return content_hash(self)

    @property
    def observed(self) -> State:
        return tuple(point.value for point in self.observations)

    @property
    def scales(self) -> State:
        return tuple(point.scale for point in self.observations)


@dataclass(frozen=True, slots=True)
class VasicekBondProblem(_ProblemValues):
    currency: Currency
    as_of: datetime
    initial_rate: float
    observations: tuple[DiscountObservation, ...]
    model_name: ClassVar[str] = "vasicek_q_bonds"
    model_version: ClassVar[str] = "0.3.0"
    parameter_names: ClassVar[tuple[str, ...]] = ("speed", "level", "volatility")
    value_unit: ClassVar[str] = "discount_factor"

    def __post_init__(self) -> None:
        _dataset(self.currency, self.as_of, self.observations, DiscountObservation)
        object.__setattr__(self, "as_of", utc_timestamp(self.as_of))
        require_finite(self.initial_rate, name="initial short rate")
        if len({point.maturity for point in self.observations}) != len(self.observations):
            raise CalibrationError("Discount observation maturities must be unique")

    def predict(self, parameters: State) -> State:
        speed, level, volatility = vector(parameters, 3, "Vasicek parameters")
        model = Vasicek(speed, level, volatility)
        return tuple(model.bond(self.initial_rate, point.maturity) for point in self.observations)


@dataclass(frozen=True, slots=True)
class HullWhiteBondOptionProblem(_ProblemValues):
    currency: Currency
    as_of: datetime
    initial_curve: LinearForwardCurve
    observations: tuple[BondOptionObservation, ...]
    model_name: ClassVar[str] = "hull_white_q_bond_calls"
    model_version: ClassVar[str] = "0.3.0"
    parameter_names: ClassVar[tuple[str, ...]] = ("speed", "volatility")
    value_unit: ClassVar[str] = "nominal_fraction"

    def __post_init__(self) -> None:
        _dataset(self.currency, self.as_of, self.observations, BondOptionObservation)
        object.__setattr__(self, "as_of", utc_timestamp(self.as_of))
        if not isinstance(self.initial_curve, LinearForwardCurve):
            raise CalibrationError(
                "Hull-White calibration requires the explicit smooth initial curve"
            )
        keys = tuple((p.expiry, p.maturity, p.strike) for p in self.observations)
        if len(set(keys)) != len(keys):
            raise CalibrationError("Bond-option instruments must be unique")
        for p in self.observations:
            upper = self.initial_curve.discount(p.maturity)
            lower = max(upper - p.strike * self.initial_curve.discount(p.expiry), 0.0)
            if not lower <= p.value <= upper:
                raise CalibrationError("Observed bond call violates no-arbitrage bounds")

    def predict(self, parameters: State) -> State:
        speed, volatility = vector(parameters, 2, "Hull-White parameters")
        model = HullWhite(speed, volatility, self.initial_curve)
        return tuple(model.bond_call(p.expiry, p.maturity, p.strike) for p in self.observations)


@dataclass(frozen=True, slots=True)
class HestonCallProblem(_ProblemValues):
    currency: Currency
    as_of: datetime
    spot: float
    rate: float
    dividend: float
    observations: tuple[CallObservation, ...]
    fourier_settings: FourierSettings = FourierSettings()
    model_name: ClassVar[str] = "heston_q_european_calls"
    model_version: ClassVar[str] = "0.3.0"
    parameter_names: ClassVar[tuple[str, ...]] = (
        "speed",
        "variance_level",
        "vol_of_variance",
        "correlation",
        "initial_variance",
    )
    value_unit: ClassVar[str] = "currency_units_per_underlying_unit"

    def __post_init__(self) -> None:
        _dataset(self.currency, self.as_of, self.observations, CallObservation)
        object.__setattr__(self, "as_of", utc_timestamp(self.as_of))
        positive(self.spot, "option spot")
        require_finite(self.rate, name="risk-free rate")
        require_finite(self.dividend, name="dividend yield")
        if not isinstance(self.fourier_settings, FourierSettings):
            raise CalibrationError("Heston calibration requires FourierSettings")
        keys = tuple((p.expiry, p.strike) for p in self.observations)
        if len(set(keys)) != len(keys):
            raise CalibrationError("Call instruments must be unique")
        # Use the exact deterministic-variance limit solely for arbitrage bounds.
        from parallax_risk.domain.models.base import checked_exp

        for p in self.observations:
            upper = self.spot * checked_exp(-self.dividend * p.expiry)
            lower = max(upper - p.strike * checked_exp(-self.rate * p.expiry), 0.0)
            if not lower <= p.value <= upper:
                raise CalibrationError("Observed European call violates no-arbitrage bounds")

    def predict(self, parameters: State) -> State:
        speed, level, xi, rho, v0 = vector(parameters, 5, "Heston parameters")
        model = Heston(speed, level, xi, rho, self.rate, self.dividend)
        return tuple(
            heston_call(model, self.spot, v0, p.strike, p.expiry, self.fourier_settings).value
            for p in self.observations
        )
