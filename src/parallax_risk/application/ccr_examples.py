"""Labelled synthetic CCR comparison with actual Monte Carlo exposure."""

import io
from dataclasses import replace
from datetime import date
from decimal import Decimal

from parallax_risk.application.ccr import CcrRunResult, CcrService
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.exposure_examples import example_inputs
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.enums import DayCount
from parallax_risk.common.identifiers import PortfolioId, RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.ccr.contracts import ComparisonPolicy, SupervisoryParameters
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine


def example(paths: int = 256) -> CcrRunResult:
    request, book, markets, run = example_inputs(paths)
    dates = (*markets.dates, date(2026, 1, 1))
    request = replace(
        request,
        grid=TimeGrid(tuple(year_fraction(book.as_of, d, DayCount.ACT_365_FIXED) for d in dates)),
    )
    markets = replace(markets, request=request, dates=dates)
    book = replace(book, portfolio_id=PortfolioId("synthetic-phase8"))
    run = replace(run, run_id=RiskRunId("synthetic-phase8"))
    logger = create_logger(stream=io.StringIO())
    workflow = CcrService(
        ExposureService(MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger)
    )
    parameters = SupervisoryParameters(
        "Research defaults drawn from CRE52, effective 2023-01-01; restricted scope"
    )
    policy = ComparisonPolicy(
        book.reporting_currency,
        Money(Decimal(1), book.reporting_currency),
        0.10,
        1.0,
        0.08,
        "Synthetic illustrative weight/ratio and exception tolerances",
    )
    return workflow.run(request, book, markets, run, parameters, policy)
