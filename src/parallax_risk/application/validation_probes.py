"""Synthetic operation-seam probes, explicitly smaller than full-engine fault injection."""

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np

from parallax_risk.application.validation_models import ProductionCvaModel
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CsaId, TradeId
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date, year_fraction
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.ccr.contracts import (
    AssetClass,
    MarginTerms,
    StandardizedInputs,
    SupervisoryParameters,
    SupervisoryTrade,
)
from parallax_risk.domain.ccr.standardized import standardized
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import exposure_at_default
from parallax_risk.domain.market.curves.interpolation import (
    LinearInterpolator,
    LogLinearInterpolator,
)
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.portfolio.csa import CollateralDirection, Csa, EligibleCollateral
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.statistics import OnlineMoments
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase
from parallax_risk.domain.validation.checks import equality
from parallax_risk.domain.validation.contracts import Check, Metric, ModelOutput, Tolerance
from parallax_risk.domain.validation.mutation import Mutation, MutationKind


@dataclass(frozen=True, slots=True)
class ProbeCase:
    cva: CvaBenchmarkCase
    start: date
    end: date
    fx: float
    correlation: float
    collateral: float
    threshold: float
    volatility: float
    mpor_business_days: int
    samples: tuple[float, ...]
    calibration_dates: tuple[date, ...]
    calibrated_hazards: tuple[float, ...]
    as_of: date

    def __post_init__(self) -> None:
        if not isinstance(self.cva, CvaBenchmarkCase):
            raise DomainValidationError("Probe requires a validated CVA case")
        for civil_date in (self.start, self.end, self.as_of, *self.calibration_dates):
            require_date(civil_date)
        require_tuple(self.samples, float, nonempty=True)
        require_tuple(self.calibration_dates, date, nonempty=True)
        require_tuple(self.calibrated_hazards, float, nonempty=True)
        integer(self.mpor_business_days, "MPOR business days")
        values = (
            self.fx,
            self.collateral,
            self.threshold,
            self.volatility,
            *self.samples,
            *self.calibrated_hazards,
        )
        for value in values:
            require_finite(value, name="probe input")
        if (
            self.start >= self.end
            or self.fx <= 0
            or self.volatility < 0
            or self.collateral < 0
            or self.threshold < 0
            or self.mpor_business_days < 10
            or len(self.samples) < 4
            or len(self.calibration_dates) != len(self.calibrated_hazards)
            or any(h < 0 for h in self.calibrated_hazards)
            or any(
                b <= a
                for a, b in zip(self.calibration_dates, self.calibration_dates[1:], strict=False)
            )
            or not any(d <= self.as_of for d in self.calibration_dates)
            or not -1 < require_finite(self.correlation, name="probe correlation") < 1
        ):
            raise DomainValidationError("Probe inputs violate date, sample or economic domains")

    @property
    def hash(self) -> str:
        return content_hash(self)


def cash_probes(case: ProbeCase, cash: float, threshold: float) -> tuple[float, float, float]:
    """Actual restricted CCR replacement cost/MF and CSA target; no regulatory inference."""
    currency = case.cva.currency

    def money(value: float) -> Money:
        return Money(Decimal(str(value)), currency)

    zero = money(0.0)
    value = money(case.cva.exposure[-1])
    horizon = case.cva.times[-1]
    trade = SupervisoryTrade(
        TradeId("operation-probe"),
        AssetClass.INTEREST_RATE,
        (currency,),
        money(100.0),
        1.0,
        horizon,
        0.0,
        horizon,
    )
    parameters = SupervisoryParameters("Labelled synthetic operation probe")
    inputs = StandardizedInputs("operation-probe", value, money(cash), (trade,))
    rc = standardized(inputs, parameters).replacement_cost
    margin = MarginTerms(zero, zero, zero, case.mpor_business_days, "Synthetic business-day MPOR")
    margined = standardized(
        StandardizedInputs("operation-probe", value, money(cash), (trade,), margin), parameters
    )
    csa = Csa(
        CsaId("operation-probe"),
        currency,
        money(threshold),
        zero,
        zero,
        zero,
        (EligibleCollateral(currency, Decimal(0)),),
        CollateralDirection.RECEIVE_ONLY,
        case.start,
        1,
        0,
        0,
    )
    target = csa.target(value)[0]
    return float(rc.amount), float(target.amount), margined.trade_contributions[0].maturity_factor


@dataclass(frozen=True, slots=True)
class OperationProbeModel:
    """One explicit operation replacement per mutant, with unchanged input evidence."""

    def evaluate(self, case: ProbeCase, mutation: Mutation | None) -> ModelOutput:
        if not isinstance(case, ProbeCase) or (
            mutation is not None and not isinstance(mutation, Mutation)
        ):
            raise DomainValidationError("Operation probe requires typed case and optional mutation")
        kind = mutation.kind if mutation is not None else None
        c = case.cva
        horizon = c.times[-1]
        df = math.exp(c.rate * horizon if kind == MutationKind.DISCOUNT else -c.rate * horizon)
        signed_cva = ProductionCvaModel().evaluate(c).metric("CVA").value
        rho = -case.correlation if kind == MutationKind.CORRELATION else case.correlation
        loadings = CorrelationMatrix(("a", "b"), ((1.0, rho), (rho, 1.0))).cholesky()
        sample = case.samples[:2] if kind == MutationKind.PATHS else case.samples
        moments = OnlineMoments()
        moments.update(np.asarray(sample))
        sem = moments.estimate(total_paths=len(sample), sampling_unit="iid_path").standard_error
        eligible = tuple(
            h
            for d, h in zip(case.calibration_dates, case.calibrated_hazards, strict=True)
            if d <= case.as_of or kind == MutationKind.LOOK_AHEAD
        )
        interpolation = (
            LinearInterpolator() if kind == MutationKind.INTERPOLATION else LogLinearInterpolator()
        )
        hazard = PiecewiseHazardCurve((0.0, horizon), (c.hazard,))
        a = c.times[-2]
        cash = 0.0 if kind == MutationKind.COLLATERAL else case.collateral
        threshold = 0.0 if kind == MutationKind.THRESHOLD else case.threshold
        volatility = 100 * case.volatility if kind == MutationKind.VOLATILITY else case.volatility
        # Exercise actual restricted cash/CSA/CCR operations at isolated seams.
        rc, target, mf = cash_probes(case, cash, threshold)
        ead = exposure_at_default(
            np.asarray([c.exposure]), c.times, ((a + horizon) / 2,)
        ).mean_with_nondefault_zero
        observations = (
            (MutationKind.DISCOUNT, df, "discount_factor"),
            (
                MutationKind.SIGN,
                -signed_cva if kind == MutationKind.SIGN else signed_cva,
                c.currency.value,
            ),
            (
                MutationKind.RECOVERY,
                c.recovery
                if kind == MutationKind.RECOVERY
                else RecoveryAssumption(c.recovery).loss_given_default,
                "LGD_fraction",
            ),
            (
                MutationKind.FX,
                100 / case.fx if kind == MutationKind.FX else 100 * case.fx,
                c.currency.value,
            ),
            (
                MutationKind.DAY_COUNT,
                year_fraction(
                    case.start,
                    case.end,
                    DayCount.ACT_360 if kind == MutationKind.DAY_COUNT else DayCount.ACT_365_FIXED,
                ),
                "years",
            ),
            (
                MutationKind.CORRELATION,
                math.fsum(x * y for x, y in zip(loadings[0], loadings[1], strict=True)),
                "correlation",
            ),
            (MutationKind.COLLATERAL, rc, c.currency.value),
            (MutationKind.THRESHOLD, target, c.currency.value),
            (
                MutationKind.DATE,
                c.exposure[-2] if kind == MutationKind.DATE else ead,
                c.currency.value,
            ),
            (MutationKind.LOOK_AHEAD, eligible[-1], "annual_hazard"),
            (
                MutationKind.VOLATILITY,
                GeometricBrownianMotion(0.0, volatility).diffusion(0.0, (100.0,))[0][0],
                "currency_per_sqrt_year",
            ),
            (MutationKind.PATHS, sem, "sample_mean_standard_error"),
            (
                MutationKind.INTERPOLATION,
                interpolation.interpolate(0.5, (0.0, 1.0), (1.0, 0.81)),
                "discount_factor",
            ),
            (
                MutationKind.MPOR,
                0.0 if kind == MutationKind.MPOR else mf,
                "margin_maturity_factor",
            ),
            (
                MutationKind.DEFAULT,
                hazard.default_probability(horizon)
                if kind == MutationKind.DEFAULT
                else hazard.default_increment(a, horizon),
                "interval_default_probability",
            ),
        )
        metrics = tuple(Metric(str(k), float(v), u) for k, v, u in observations)
        return ModelOutput(
            case.hash,
            "isolated-operation-probes",
            "0.10.0",
            metrics,
            content_hash((case.hash, mutation, metrics)),
            (
                "Labelled synthetic operation probes; no global production modification",
                "Restricted cash/threshold/MPOR seams and dated calibration-selection proxy; "
                "not full CSA or calibration pipelines",
                "Fault-free sign metric invokes the actual production credit integral",
            ),
        )


def probe_suite(
    output: ModelOutput, targets: tuple[Metric, ...], tolerance: Tolerance
) -> tuple[Check, ...]:
    """Independent caller targets with exact metric/unit schemas; selected subset permitted."""
    require_tuple(targets, Metric, nonempty=True)
    if len({t.name for t in targets}) != len(targets):
        raise DomainValidationError("Probe target names must be unique")
    checks = []
    for target in targets:
        actual = output.metric(target.name)
        if actual.schema != target.schema:
            raise DomainValidationError("Probe target units/schema do not match")
        checks.append(
            equality(
                f"probe-{target.name}",
                actual,
                target.value,
                tolerance,
                evidence=(output.hash, content_hash(target)),
                reproduction="Retain ProbeCase, Mutation and independent targets",
                version=output.model_version,
            )
        )
    return tuple(checks)
