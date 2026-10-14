"""Labelled synthetic validation lab; failed numerical findings remain in the report."""

import io
import math
from dataclasses import dataclass, replace

from parallax_risk.application.calibration import CalibrationSolver
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.validation import ValidationLab, calibration_band, perturbation_band
from parallax_risk.application.validation_invariants import cva_invariants
from parallax_risk.application.validation_models import ProductionCvaModel, ProductionXvaModel
from parallax_risk.application.validation_stress import (
    ScenarioKind,
    StressResult,
    StressScenario,
    combine,
    stress,
)
from parallax_risk.application.xva import AdditiveXvaCalculator, XvaService
from parallax_risk.application.xva_examples import experiment
from parallax_risk.application.xva_revaluation import FactorMove, XvaExperiment, XvaRevaluation
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.calibration.contracts import CalibrationSettings, ParameterBound
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.benchmark import (
    CvaBenchmarkCase,
    FlatHazardProbabilityProblem,
    IndependentCvaBenchmark,
)
from parallax_risk.domain.validation.checks import (
    ConvergenceAxis,
    ConvergenceStudy,
    SensitivityValidation,
    sensitivity,
)
from parallax_risk.domain.validation.contracts import Check, Comparison, ModelOutput, Tolerance
from parallax_risk.domain.validation.uncertainty import IidUnitResampler, UncertaintyBand, bootstrap
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor


def path_case(case: XvaExperiment, count: int) -> XvaExperiment:
    request = replace(case.request, path_count=count)
    return replace(case, request=request, markets=replace(case.markets, request=request))


def refined_case(case: XvaExperiment) -> XvaExperiment:
    """Midpoint civil dates, constant external IM only; no arbitrary profile interpolation."""
    from parallax_risk.common.errors import DomainValidationError

    if any(len(set(m.posted_initial_margin)) != 1 for m in case.margins):
        raise DomainValidationError(
            "Synthetic refinement helper supports constant supplied IM only"
        )
    dates = tuple(
        sorted(
            set(case.markets.dates)
            | {
                a + (b - a) // 2
                for a, b in zip(case.markets.dates, case.markets.dates[1:], strict=False)
            }
        )
    )
    times = tuple(year_fraction(dates[0], date, DayCount.ACT_365_FIXED) for date in dates)
    request = replace(case.request, grid=TimeGrid(times))
    return replace(
        case,
        request=request,
        markets=replace(case.markets, request=request, dates=dates),
        margins=tuple(
            replace(
                m, times=times, posted_initial_margin=(m.posted_initial_margin[0],) * len(times)
            )
            for m in case.margins
        ),
    )


@dataclass(frozen=True, slots=True)
class ValidationResearchResult:
    benchmark_inputs: CvaBenchmarkCase
    comparison: Comparison
    invariants: tuple[Check, ...]
    xva_inputs: XvaExperiment
    baseline: ModelOutput
    local_fx: SensitivityValidation
    paths: ConvergenceStudy
    time_steps: ConvergenceStudy
    bootstrap_cva: UncertaintyBand
    parameter_cva: UncertaintyBand
    calibration_cva: UncertaintyBand
    stresses: tuple[StressResult, ...]


def example(solver: CalibrationSolver, paths: int = 16) -> ValidationResearchResult:
    benchmark = CvaBenchmarkCase(
        (0.0, 0.25, 0.5, 0.75, 1.0), (100.0,) * 5, Currency.USD, 0.03, 0.2, 0.4
    )
    cva = ProductionCvaModel()
    reproduction = (
        "Retain 0.9.0 source/wheel and run python scripts/demo_validation.py; "
        "all inputs are synthetic"
    )
    comparison = ValidationLab(cva, IndependentCvaBenchmark()).compare(
        benchmark, Tolerance(1e-4), reproduction
    )
    invariants = cva_invariants(cva, benchmark, Tolerance(1e-10, 1e-12), reproduction)
    inputs = experiment(paths)
    logger = create_logger(stream=io.StringIO())
    model = ProductionXvaModel(
        XvaRevaluation(
            ExposureService(
                MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger
            ),
            XvaService(AdditiveXvaCalculator(), logger),
        )
    )
    baseline = model.evaluate(inputs)
    factor = RiskFactor(FactorKind.FX, "fx")
    local = sensitivity(
        lambda amount: model.evaluate(model.workflow.bump(inputs, factor, amount)).metric("CVA"),
        0.001,
        "direct_QUOTE_per_BASE",
        Tolerance(0.01, 1e-3),
        evidence=(inputs.hash,),
        reproduction=reproduction,
        version=baseline.model_version,
    )
    ladder = tuple(path_case(inputs, n) for n in (paths, paths * 2, paths * 4))
    path_study = model.convergence(
        ladder,
        "CVA",
        ConvergenceAxis.PATH_COUNT,
        Tolerance(0.05, 0.05),
        Tolerance(0.05, 0.05),
        reproduction,
    )
    step_study = model.convergence(
        (inputs, refined_case(inputs)),
        "CVA",
        ConvergenceAxis.TIME_STEP,
        Tolerance(0.05, 0.05),
        Tolerance(0.05, 0.05),
        reproduction,
    )
    data = model.observations(ladder[-1], "CVA")
    band = bootstrap(
        data,
        StreamKey(inputs.run.seed, 900, 0),
        IidUnitResampler(),
        lambda values: math.fsum(values) / len(values),
        statistic_name="signed_CVA_mean",
        replicates=128,
    )
    parameter = perturbation_band(
        cva, benchmark, tuple(replace(benchmark, recovery=r) for r in (0.3, 0.4, 0.5)), "CVA"
    )
    times = (0.25, 0.5, 1.0, 2.0, 3.0)
    observed = tuple(
        -math.expm1(-0.2 * t) + (1e-4 if i % 2 else -1e-4) for i, t in enumerate(times)
    )
    problem = FlatHazardProbabilityProblem(
        times,
        observed,
        (0.01,) * 5,
        "Synthetic flat-hazard probabilities with declared deterministic quote perturbations",
    )
    calibration = solver.solve(
        problem,
        (ParameterBound("hazard", 0.1, 0.0, 1.0),),
        CalibrationSettings(),
        CalibrationRunId("synthetic-validation-hazard"),
    )
    calibration_result = calibration_band(
        calibration,
        lambda parameters: cva.evaluate(replace(benchmark, hazard=parameters[0])),
        "CVA",
        (1e-4,),
        ("annual_decimal_hazard",),
    )
    spot = StressScenario(
        "synthetic-spot-up",
        ScenarioKind.HYPOTHETICAL,
        (FactorMove("spot", factor, 0.05),),
        "Synthetic user-defined shock",
        "Direct FX spot +0.05 QUOTE/BASE",
    )
    recovery = StressScenario(
        "synthetic-recovery-down",
        ScenarioKind.HYPOTHETICAL,
        (FactorMove("recovery", RiskFactor(FactorKind.RECOVERY, "synthetic-cp"), -0.1),),
        "Synthetic user-defined shock",
        "Recovery -0.1 with hazard held fixed",
    )
    stresses = stress(
        model,
        inputs,
        (
            spot,
            recovery,
            combine("synthetic-combined", (spot, recovery), "Ordered spot then recovery"),
        ),
    )
    return ValidationResearchResult(
        benchmark,
        comparison,
        invariants,
        inputs,
        baseline,
        local,
        path_study,
        step_study,
        band,
        parameter,
        calibration_result,
        stresses,
    )
