"""Actual production CVA/XVA adapters and path/step studies, isolated from HTTP/storage."""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from parallax_risk.application.xva_revaluation import XvaExperiment, XvaRevaluation
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CurveId
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import DependenceKind
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.pricing._numbers import money_value, total
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.random import SequenceKind
from parallax_risk.domain.simulation.statistics import OnlineMoments, SamplingUnit, sampling_units
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase, benchmark_output
from parallax_risk.domain.validation.checks import (
    ConvergenceAxis,
    ConvergencePoint,
    ConvergenceStudy,
    convergence,
)
from parallax_risk.domain.validation.contracts import Contribution, Metric, ModelOutput, Tolerance
from parallax_risk.domain.validation.uncertainty import IndependentObservations
from parallax_risk.domain.xva.calculators import credit_integral


@dataclass(frozen=True, slots=True)
class ProductionCvaModel:
    """Exercise the actual production credit integral; fixed computational epoch, no feed."""

    def evaluate(self, case: CvaBenchmarkCase) -> ModelOutput:
        if not isinstance(case, CvaBenchmarkCase):
            raise DomainValidationError("Production benchmark adapter needs a CVA case")
        curve = DiscountCurve(
            CurveId("validation-flat-discount"),
            case.currency,
            date(2000, 1, 1),
            DayCount.ACT_365_FIXED,
            case.times,
            tuple(math.exp(-case.rate * t) for t in case.times),
            InterpolationKind.LOG_LINEAR,
            ExtrapolationPolicy.ERROR,
        )
        values = credit_integral(
            case.times,
            case.exposure,
            curve,
            PiecewiseHazardCurve((0.0, case.times[-1]), (case.hazard,)),
            RecoveryAssumption(case.recovery),
        )
        return benchmark_output(
            case,
            "production-cva",
            -total(values),
            "production_endpoint_average_discounted_EE_exact_PD_increments",
        )


@dataclass(frozen=True, slots=True)
class ProductionXvaModel:
    workflow: XvaRevaluation

    def evaluate(self, case: XvaExperiment) -> ModelOutput:
        result = self.workflow.value(case)
        r = result.result
        parts = tuple(Contribution(str(c.kind), money_value(c.adjustment)) for c in r.components)
        metrics = tuple(Metric(c.name, c.value, r.currency.value) for c in parts) + (
            Metric("TOTAL", money_value(r.total_adjustment), r.currency.value, parts),
        )
        return ModelOutput(
            case.hash,
            "production-xva",
            r.model_version,
            metrics,
            content_hash((result.exposure_hash, r.hash)),
            r.assumptions,
        )

    def observations(self, case: XvaExperiment, metric: str) -> IndependentObservations:
        """Linear independent-credit CVA and full-horizon EPE independent sampling units."""
        if not isinstance(case, XvaExperiment) or metric not in ("CVA", "EPE"):
            raise DomainValidationError("Path observations support independent CVA and EPE only")
        if case.request.sequence.kind != SequenceKind.PSEUDO:
            raise DomainValidationError("Single Sobol design is not an independent path sample")
        if metric == "CVA" and any(c.kind != DependenceKind.INDEPENDENT for c in case.credit):
            raise DomainValidationError("Path CVA observations require independent credit")
        paths = self.workflow.exposure.run(
            case.request,
            case.book,
            case.markets,
            case.run,
            accounts=case.accounts,
            credit=case.credit,
        )
        values = []
        times = case.request.grid.times
        for path in paths.positive_paths.array:
            if metric == "EPE":
                value = total(
                    tuple(
                        float(np.trapezoid(path[:, j], np.asarray(times)) / times[-1])
                        for j in range(path.shape[1])
                    )
                )
            else:
                value = -total(
                    tuple(
                        total(
                            credit_integral(
                                times,
                                tuple(float(v) for v in path[:, j]),
                                case.discount,
                                c.baseline,
                                c.recovery,
                            )
                        )
                        for j, c in enumerate(case.credit)
                    )
                )
            values.append(value)
        units = sampling_units(
            np.asarray(values, dtype=np.float64), antithetic=case.request.sequence.antithetic
        )
        convention: SamplingUnit = (
            "antithetic_pair" if case.request.sequence.antithetic else "iid_path"
        )
        return IndependentObservations(
            metric,
            case.book.reporting_currency.value,
            tuple(float(v) for v in units),
            convention,
            case.request.path_count,
            content_hash((case.hash, paths.market_path_digest, paths.positive_paths.hash, metric)),
        )

    def convergence(
        self,
        cases: tuple[XvaExperiment, ...],
        metric: str,
        axis: ConvergenceAxis,
        stability: Tolerance,
        precision: Tolerance,
        reproduction: str,
        *,
        confidence: float = 0.95,
        maximum_evaluations: int = 100,
    ) -> ConvergenceStudy:
        """Caller supplies actual complete path/grid experiments, including civil dates/IM."""
        require_tuple(cases, XvaExperiment, nonempty=True)
        integer(maximum_evaluations, "convergence evaluation budget")
        if (
            len(cases) < 2
            or len(cases) > maximum_evaluations
            or not isinstance(axis, ConvergenceAxis)
        ):
            raise DomainValidationError("Convergence ladder/budget/axis invalid")
        base = cases[0]
        # Changes to dates/request-bound markets/IM grids are permitted only for step studies.
        if any(
            (
                c.book,
                c.credit,
                c.accounts,
                c.own,
                c.discount,
                c.funding,
                c.run,
                c.request.components,
                c.request.sequence,
                c.request.correlation,
                c.markets.rates,
                c.markets.fx,
                c.markets.knot_dates,
                c.markets.initial_fixings,
            )
            != (
                base.book,
                base.credit,
                base.accounts,
                base.own,
                base.discount,
                base.funding,
                base.run,
                base.request.components,
                base.request.sequence,
                base.request.correlation,
                base.markets.rates,
                base.markets.fx,
                base.markets.knot_dates,
                base.markets.initial_fixings,
            )
            for c in cases
        ):
            raise DomainValidationError(
                "Convergence cannot silently change economic inputs or streams"
            )
        if any(c.request.grid.times[-1] != base.request.grid.times[-1] for c in cases):
            raise DomainValidationError("Convergence horizons must match")
        if axis == ConvergenceAxis.PATH_COUNT and any(
            (c.request.grid, c.markets.dates, c.margins)
            != (base.request.grid, base.markets.dates, base.margins)
            for c in cases
        ):
            raise DomainValidationError(
                "Path convergence must retain the time grid and margin profiles"
            )
        if axis == ConvergenceAxis.TIME_STEP and any(
            c.request.path_count != base.request.path_count for c in cases
        ):
            raise DomainValidationError("Step convergence must retain path count")
        points = []
        for case in cases:
            data = self.observations(case, metric)
            moments = OnlineMoments()
            moments.update(np.asarray(data.values))
            estimate = moments.estimate(
                total_paths=data.total_paths,
                sampling_unit=data.sampling_unit,
                confidence=confidence,
            )
            resolution = (
                float(case.request.path_count)
                if axis == ConvergenceAxis.PATH_COUNT
                else max(
                    b - a
                    for a, b in zip(
                        case.request.grid.times, case.request.grid.times[1:], strict=False
                    )
                )
            )
            points.append(ConvergencePoint(resolution, estimate, case.hash))
        return convergence(
            axis,
            metric,
            base.book.reporting_currency.value,
            tuple(points),
            stability,
            precision,
            reproduction=reproduction,
            version="0.7.0",
        )
