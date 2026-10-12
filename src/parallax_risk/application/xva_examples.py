"""Labelled synthetic XVA/risk research with full production revaluation."""

import io
import math
from dataclasses import dataclass, replace

from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.exposure_examples import example_credit, example_inputs
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.xva import AdditiveXvaCalculator, XvaRunResult, XvaService
from parallax_risk.application.xva_revaluation import FactorMove, XvaExperiment, XvaRevaluation
from parallax_risk.common.enums import DayCount
from parallax_risk.common.identifiers import CurveId, PortfolioId, RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.xva.contracts import (
    FundingSpreadCurve,
    FundingTerms,
    MarginProfile,
    OwnCredit,
)
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor, XvaAttribution, XvaSensitivity


def experiment(paths: int = 64) -> XvaExperiment:
    """Synthetic equal-rate FX book; fixed external IM and funding inputs, no calibration."""
    request, book, markets, run = example_inputs(paths)
    book = replace(book, portfolio_id=PortfolioId("synthetic-phase7"))
    run = replace(run, run_id=RiskRunId("synthetic-phase7"))
    times = request.grid.times
    spreads = tuple(FundingSpreadCurve((0.0, times[-1]), (s,)) for s in (0.01, 0.005, 0.02))
    discount = DiscountCurve(
        CurveId("synthetic-xva-discount"),
        book.reporting_currency,
        book.as_of,
        DayCount.ACT_365_FIXED,
        times,
        tuple(math.exp(-0.03 * t) for t in times),
        InterpolationKind.LOG_LINEAR,
        ExtrapolationPolicy.ERROR,
    )
    return XvaExperiment(
        request,
        book,
        markets,
        (),
        (example_credit(request, book)[0],),
        OwnCredit(PiecewiseHazardCurve((0.0, times[-1]), (0.1,)), RecoveryAssumption(0.4)),
        discount,
        FundingTerms(spreads[0], spreads[1], spreads[2], True),
        (
            MarginProfile(
                book.reporting_currency,
                times,
                (10.0,) * len(times),
                "Synthetic externally supplied expected segregated posted IM",
            ),
        ),
        run,
    )


@dataclass(frozen=True, slots=True)
class XvaResearchResult:
    inputs: XvaExperiment
    credit_scenarios: tuple[CreditScenario, ...]
    valuations: tuple[XvaRunResult, ...]
    fx_sensitivity: XvaSensitivity
    attribution: XvaAttribution


def example(paths: int = 64) -> XvaResearchResult:
    """Three credit cases, five actual FX repricings and ordered spot/credit movements."""
    inputs = experiment(paths)
    logger = create_logger(stream=io.StringIO())
    workflow = XvaRevaluation(
        ExposureService(MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger),
        XvaService(AdditiveXvaCalculator(), logger),
    )
    scenarios = example_credit(inputs.request, inputs.book)
    valuations = tuple(workflow.value(replace(inputs, credit=(c,))) for c in scenarios)
    fx = RiskFactor(FactorKind.FX, "fx")
    credit = RiskFactor(FactorKind.CREDIT_SPREAD, "synthetic-cp")
    moves = (FactorMove("spot", fx, 0.02), FactorMove("credit", credit, 0.002))
    actual = workflow.bump(workflow.bump(inputs, fx, 0.02), credit, 0.002)
    return XvaResearchResult(
        inputs,
        scenarios,
        valuations,
        workflow.sensitivity(inputs, fx, 0.001),
        workflow.attribute(inputs, moves, actual),
    )
