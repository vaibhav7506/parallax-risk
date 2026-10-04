"""Strict Pydantic calibration ingestion; explicit domain mapping, no file or HTTP IO."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator

from parallax_risk.application.market_data import SourceInput
from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import CalibrationRunId, QuoteId
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain.calibration.contracts import (
    CalibrationProblem,
    CalibrationSettings,
    ParameterBound,
)
from parallax_risk.domain.calibration.problems import (
    BondOptionObservation,
    CallObservation,
    DiscountObservation,
    HestonCallProblem,
    HullWhiteBondOptionProblem,
    VasicekBondProblem,
)
from parallax_risk.domain.models.heston_pricing import FourierSettings
from parallax_risk.domain.models.rates import LinearForwardCurve


class CalibrationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class QuoteInput(CalibrationInput):
    quote_id: str
    value: StrictFloat
    source: SourceInput
    scale: StrictFloat = 1.0


class DiscountInput(QuoteInput):
    maturity: StrictFloat


class BondOptionInput(QuoteInput):
    expiry: StrictFloat
    maturity: StrictFloat
    strike: StrictFloat


class CallInput(QuoteInput):
    expiry: StrictFloat
    strike: StrictFloat


class ProblemInput(CalibrationInput):
    currency: Currency
    as_of: datetime

    @field_validator("as_of", mode="before")
    @classmethod
    def explicit_instant(cls, value: object) -> datetime:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError("Calibration as-of requires an explicitly zoned instant")
        return utc_timestamp(value)


class VasicekInput(ProblemInput):
    kind: Literal["vasicek"]
    initial_rate: StrictFloat
    observations: tuple[DiscountInput, ...]

    def to_domain(self) -> VasicekBondProblem:
        return VasicekBondProblem(
            self.currency,
            self.as_of,
            self.initial_rate,
            tuple(
                DiscountObservation(
                    QuoteId(p.quote_id), p.maturity, p.value, p.source.to_domain(), p.scale
                )
                for p in self.observations
            ),
        )


class HullWhiteInput(ProblemInput):
    kind: Literal["hull_white"]
    forward_level: StrictFloat
    forward_slope: StrictFloat = 0.0
    observations: tuple[BondOptionInput, ...]

    def to_domain(self) -> HullWhiteBondOptionProblem:
        return HullWhiteBondOptionProblem(
            self.currency,
            self.as_of,
            LinearForwardCurve(self.forward_level, self.forward_slope),
            tuple(
                BondOptionObservation(
                    QuoteId(p.quote_id),
                    p.expiry,
                    p.maturity,
                    p.strike,
                    p.value,
                    p.source.to_domain(),
                    p.scale,
                )
                for p in self.observations
            ),
        )


class FourierInput(CalibrationInput):
    absolute_price_tolerance: StrictFloat = 1e-7
    relative_tolerance: StrictFloat = 1e-9
    subdivision_limit: StrictInt = 250

    def to_domain(self) -> FourierSettings:
        return FourierSettings(
            self.absolute_price_tolerance, self.relative_tolerance, self.subdivision_limit
        )


class HestonInput(ProblemInput):
    kind: Literal["heston"]
    spot: StrictFloat
    rate: StrictFloat
    dividend: StrictFloat
    observations: tuple[CallInput, ...]
    fourier_settings: FourierInput = FourierInput()

    def to_domain(self) -> HestonCallProblem:
        return HestonCallProblem(
            self.currency,
            self.as_of,
            self.spot,
            self.rate,
            self.dividend,
            tuple(
                CallObservation(
                    QuoteId(p.quote_id), p.expiry, p.strike, p.value, p.source.to_domain(), p.scale
                )
                for p in self.observations
            ),
            self.fourier_settings.to_domain(),
        )


class BoundInput(CalibrationInput):
    name: str
    initial: StrictFloat
    lower: StrictFloat
    upper: StrictFloat

    def to_domain(self) -> ParameterBound:
        return ParameterBound(self.name, self.initial, self.lower, self.upper)


class OptimizerInput(CalibrationInput):
    max_evaluations: StrictInt = 1000
    function_tolerance: StrictFloat = 1e-10
    parameter_tolerance: StrictFloat = 1e-10
    gradient_tolerance: StrictFloat = 1e-10
    maximum_condition_number: StrictFloat = 1e10

    def to_domain(self) -> CalibrationSettings:
        return CalibrationSettings(
            self.max_evaluations,
            self.function_tolerance,
            self.parameter_tolerance,
            self.gradient_tolerance,
            self.maximum_condition_number,
        )


class CalibrationRequest(CalibrationInput):
    """Discriminated model payload; numeric strings/bools/nonfinite values are rejected."""

    calibration_id: str
    problem: Annotated[VasicekInput | HullWhiteInput | HestonInput, Field(discriminator="kind")]
    bounds: tuple[BoundInput, ...]
    optimizer_settings: OptimizerInput = OptimizerInput()

    def to_domain(
        self,
    ) -> tuple[
        CalibrationProblem, tuple[ParameterBound, ...], CalibrationSettings, CalibrationRunId
    ]:
        return (
            self.problem.to_domain(),
            tuple(b.to_domain() for b in self.bounds),
            self.optimizer_settings.to_domain(),
            CalibrationRunId(self.calibration_id),
        )
