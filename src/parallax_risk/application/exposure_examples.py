"""Labelled synthetic exposure/WWR experiment using the actual production workflow."""

import io
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

from parallax_risk.application.context import RunContext
from parallax_risk.application.exposure import ExposureRunResult, ExposureService
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import (
    CounterpartyId,
    NettingSetId,
    PortfolioId,
    PortfolioVersion,
    RiskRunId,
    TradeId,
)
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.credit.dependence import ReducedFormSpread
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario, DependenceKind
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario, FxBinding, RateBinding
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.rates import Vasicek
from parallax_risk.domain.portfolio.contracts import (
    Counterparty,
    NettingSet,
    PortfolioSnapshot,
    Trade,
)
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.contracts import (
    ProcessComponent,
    Scheme,
    SimulationRequest,
    TimeGrid,
)
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import SequenceSpec, StreamKey


def example_inputs(
    paths: int = 256,
) -> tuple[SimulationRequest, PortfolioSnapshot, ConditionalMarketScenario, RunContext]:
    """Equal deterministic currency rates and zero FX drift for this Q synthetic case."""
    origin = date(2025, 1, 1)
    dates = (origin, date(2025, 4, 1), date(2025, 7, 1), date(2025, 10, 1))
    components = tuple(
        ProcessComponent(
            name, Vasicek(0.4, 0.03, 0), (0.03,), Scheme.EXACT, ("decimal_annual_rate",), "Q"
        )
        for name in ("usd", "eur")
    ) + (
        ProcessComponent(
            "fx", GeometricBrownianMotion(0, 0.5), (1.1,), Scheme.EXACT, ("USD/EUR",), "Q"
        ),
        ProcessComponent(
            "spread",
            GeometricBrownianMotion(0, 0.8),
            (0.12,),
            Scheme.EXACT,
            ("decimal_annual_spread",),
            "Q",
        ),
    )
    matrix = tuple(
        tuple(1.0 if i == j else 0.7 if {i, j} == {2, 3} else 0.0 for j in range(4))
        for i in range(4)
    )
    request = SimulationRequest(
        components,
        TimeGrid(tuple(year_fraction(origin, d, DayCount.ACT_365_FIXED) for d in dates)),
        paths,
        min(paths, 64),
        SequenceSpec(StreamKey(20261001)),
        CorrelationMatrix(tuple(n for c in components for n in c.factor_names), matrix),
    )
    maturity = date(2026, 1, 1)
    record = Trade(
        TradeId("synthetic-fx"),
        FxForward(
            Money(Decimal(100), Currency.EUR),
            Currency.USD,
            Decimal("1.1"),
            maturity,
            FxDirection.BUY_BASE,
        ),
        Decimal(1),
        origin,
        origin,
    )
    book = PortfolioSnapshot(
        PortfolioId("synthetic-phase6"),
        PortfolioVersion("1"),
        origin,
        Currency.USD,
        (
            Counterparty(
                CounterpartyId("synthetic-cp"),
                "Synthetic entity",
                (
                    NettingSet(
                        NettingSetId("synthetic-set"),
                        "Synthetic legal scope; not a legal opinion",
                        True,
                        Currency.USD,
                        (record,),
                    ),
                ),
            ),
        ),
    )
    market = ConditionalMarketScenario(
        request,
        dates,
        (*dates[1:], maturity, date(2027, 1, 1)),
        (RateBinding(Currency.USD, "usd"), RateBinding(Currency.EUR, "eur")),
        (FxBinding(Currency.EUR, Currency.USD, "fx"),),
    )
    run = RunContext(
        RiskRunId("synthetic-phase6"), datetime(2025, 1, 1, tzinfo=UTC), 20261001, "a" * 64
    )
    return request, book, market, run


def example_credit(
    request: SimulationRequest, book: PortfolioSnapshot
) -> tuple[CreditScenario, ...]:
    """Independent deterministic, marginal-preserving static, and dynamic spread scenarios."""
    baseline = CreditScenario(
        book.counterparties[0].counterparty_id,
        PiecewiseHazardCurve((0.0, request.grid.times[-1]), (0.2,)),
        RecoveryAssumption(0.4),
        StreamKey(request.sequence.key.seed, 1),
    )
    return (
        baseline,
        replace(
            baseline,
            kind=DependenceKind.STATIC_RANK,
            rho=0.7,
            rank_key=StreamKey(request.sequence.key.seed, 2),
        ),
        replace(
            baseline,
            kind=DependenceKind.DYNAMIC_SPREAD,
            spread_component="spread",
            spread_policy=ReducedFormSpread(baseline.recovery),
        ),
    )


def example(paths: int = 256) -> tuple[ExposureRunResult, ...]:
    """Reuse exact market paths/thresholds across all three cases; no financial API or CVA."""
    request, book, market, run = example_inputs(paths)
    logger = create_logger(stream=io.StringIO())
    workflow = ExposureService(
        MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger
    )
    return tuple(
        workflow.run(request, book, market, run, credit=(c,)) for c in example_credit(request, book)
    )
