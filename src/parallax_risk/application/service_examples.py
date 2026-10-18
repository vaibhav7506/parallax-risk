"""Explicitly synthetic full service inputs; real engines compute all outputs.

No network, filesystem or database access; composition scripts own those resources.
The small path counts demonstrate workflow/replay, not production tail accuracy.
"""

import math
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from parallax_risk.application.adversarial_examples import mutations, probe_case, probe_targets
from parallax_risk.application.ccr import ScopeMargin
from parallax_risk.application.context import RunContext
from parallax_risk.application.validation_examples import path_case
from parallax_risk.application.validation_stress import ScenarioKind, StressScenario, factor_unit
from parallax_risk.application.workflows import (
    AdversarialCommand,
    CalibrationCommand,
    CapitalCommand,
    Command,
    ComparisonCommand,
    ConvergenceCommand,
    CurveCommand,
    ExposureCommand,
    InvariantsCommand,
    MutationCommand,
    Operation,
    PortfolioCommand,
    SensitivityCommand,
    SimulationCommand,
    StressCommand,
    TradeCommand,
    UncertaintyCommand,
    XvaCommand,
)
from parallax_risk.application.xva_examples import experiment
from parallax_risk.application.xva_revaluation import FactorMove, XvaExperiment
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import (
    CalibrationRunId,
    CollateralAccountId,
    CsaId,
    CurveId,
    PortfolioId,
    QuoteId,
    RiskRunId,
)
from parallax_risk.common.money import Money
from parallax_risk.domain.calibration.contracts import CalibrationSettings, ParameterBound
from parallax_risk.domain.calibration.problems import DiscountObservation, VasicekBondProblem
from parallax_risk.domain.ccr.contracts import ComparisonPolicy, MarginTerms, SupervisoryParameters
from parallax_risk.domain.market.curves.bootstrap import BootstrapSettings, DepositQuote
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.observations import SourceMetadata
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.rates import Vasicek
from parallax_risk.domain.portfolio.collateral import CollateralAccount
from parallax_risk.domain.portfolio.csa import CollateralDirection, Csa, EligibleCollateral
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.observables import TerminalObservable
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase
from parallax_risk.domain.validation.checks import ConvergenceAxis
from parallax_risk.domain.validation.contracts import Tolerance
from parallax_risk.domain.validation.search import SearchDimension, SearchSpec
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor


def calibration() -> CalibrationCommand:
    truth = Vasicek(0.7, 0.04, 0.015)
    instant = datetime(2025, 1, 1, tzinfo=UTC)
    source = SourceMetadata(
        "synthetic-phase12",
        "Generated Q-model discount bonds; not observed market data",
        instant,
        True,
    )
    times = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    problem = VasicekBondProblem(
        Currency.USD,
        instant,
        0.03,
        tuple(
            DiscountObservation(QuoteId("synthetic-bond-" + str(i)), t, truth.bond(0.03, t), source)
            for i, t in enumerate(times)
        ),
    )
    bounds = (
        ParameterBound("speed", 0.5, 0.05, 2.0),
        ParameterBound("level", 0.03, 0.001, 0.1),
        ParameterBound("volatility", 0.01, 0.001, 0.05),
    )
    return CalibrationCommand(
        problem,
        bounds,
        CalibrationSettings(),
        CalibrationRunId("synthetic-phase12-calibration"),
        RunContext(
            RiskRunId("synthetic-phase12-calibration"),
            instant,
            20261001,
            content_hash((problem, bounds, CalibrationSettings())),
        ),
    )


def case(paths: int = 8, fitted: tuple[float, ...] | None = None) -> XvaExperiment:
    base = experiment(paths)
    components = tuple(
        replace(c, process=replace(c.process, volatility=float(c.process.volatility)))
        if isinstance(c.process, Vasicek)
        else replace(c, process=replace(c.process, drift_rate=float(c.process.drift_rate)))
        if isinstance(c.process, GeometricBrownianMotion)
        else c
        for c in base.request.components
    )
    # Thirty daily steps exercise actual margin calls without implying tail accuracy.
    dates = tuple(base.book.as_of + timedelta(days=i) for i in range(31))
    times = tuple(i / 365 for i in range(31))
    request = replace(base.request, grid=TimeGrid(times), components=components)
    base = replace(
        base,
        request=request,
        markets=replace(base.markets, request=request, dates=dates),
        discount=replace(
            base.discount, times=times, discount_factors=tuple(math.exp(-0.03 * t) for t in times)
        ),
        credit=tuple(
            replace(c, baseline=replace(c.baseline, times=(0.0, times[-1]))) for c in base.credit
        ),
        own=replace(base.own, hazard=replace(base.own.hazard, times=(0.0, times[-1]))),
        margins=tuple(
            replace(m, times=times, posted_initial_margin=(10.0,) * len(times))
            for m in base.margins
        ),
    )
    if fitted is not None:
        process = Vasicek(*fitted)
        request = replace(
            base.request,
            components=tuple(
                replace(c, process=process) if isinstance(c.process, Vasicek) else c
                for c in base.request.components
            ),
        )
        base = replace(base, request=request, markets=replace(base.markets, request=request))
    zero = Money(Decimal(0), Currency.USD)
    csa = Csa(
        CsaId("synthetic-phase12-csa"),
        Currency.USD,
        Money(Decimal(5), Currency.USD),
        Money(Decimal(5), Currency.USD),
        zero,
        zero,
        (EligibleCollateral(Currency.USD, Decimal(0)),),
        CollateralDirection.TWO_WAY,
        base.book.as_of,
        1,
        0,
        10,
    )
    netting = replace(base.book.counterparties[0].netting_sets[0], csa=csa)
    book = replace(
        base.book,
        portfolio_id=PortfolioId("synthetic-phase12"),
        counterparties=(replace(base.book.counterparties[0], netting_sets=(netting,)),),
    )
    account = CollateralAccount(
        CollateralAccountId("synthetic-phase12-account"),
        netting.netting_set_id,
        csa.csa_id,
        book.as_of,
        (zero,),
    )
    return replace(
        base,
        book=book,
        accounts=(account,),
        run=replace(base.run, run_id=RiskRunId("synthetic-phase12")),
    )


def commands(paths: int = 8, fitted: tuple[float, ...] | None = None) -> dict[Operation, Command]:
    inputs = case(paths, fitted)
    batch = next(MonteCarloEngine().iter_batches(inputs.request))
    market = next(inputs.markets.path(inputs.book, batch, 0))
    record = inputs.book.counterparties[0].netting_sets[0].trades[0]
    benchmark = CvaBenchmarkCase(
        (0.0, 0.5, 1.0), (100.0, 100.0, 100.0), Currency.USD, 0.03, 0.2, 0.4
    )
    reproduction = (
        "Retain schema-1 job input and replay using Parallax Risk 0.12.0; all inputs synthetic"
    )
    factor = RiskFactor(FactorKind.RECOVERY, "synthetic-cp")
    scenario = StressScenario(
        "synthetic-recovery-down",
        ScenarioKind.HYPOTHETICAL,
        (FactorMove("recovery", factor, -0.05),),
        "Synthetic explicit recovery movement",
        "Sensitivity exploration, not a historical observation",
    )
    capital_dates = tuple(inputs.book.as_of + timedelta(days=i) for i in range(366))
    request = replace(
        inputs.request,
        grid=TimeGrid(tuple((d - inputs.book.as_of).days / 365 for d in capital_dates)),
    )
    markets = replace(inputs.markets, request=request, dates=capital_dates)
    zero = Money(Decimal(0), Currency.USD)
    terms = MarginTerms(
        Money(Decimal(5), Currency.USD),
        zero,
        zero,
        10,
        "Synthetic explicitly supplied business-day policy; not regulatory approval",
    )
    margin = ScopeMargin(inputs.book.counterparties[0].netting_sets[0].netting_set_id, terms)
    spec = SearchSpec(
        (
            SearchDimension(
                "recovery_delta",
                factor_unit(factor),
                -0.02,
                0.02,
                "Synthetic bounded absolute recovery perturbation",
            ),
        ),
        (),
        StreamKey(20261001, 99),
        "CVA",
        "Synthetic independent-credit disagreement exploration",
        maximum_iterations=0,
        population_multiplier=5,
        maximum_evaluations=5,
    )
    probes = probe_case()
    # The enum's exact metric name is authoritative; never silently substitute a target.
    from parallax_risk.domain.validation.mutation import MutationKind

    weak_targets = tuple(m for m in probe_targets(probes) if m.name == str(MutationKind.SIGN))
    return {
        Operation.CURVE: CurveCommand(
            (
                DepositQuote(
                    QuoteId("synthetic-deposit"),
                    Currency.USD,
                    date(2026, 1, 1),
                    0.03,
                    DayCount.ACT_365_FIXED,
                ),
            ),
            CurveId("synthetic-phase12-bootstrap"),
            Currency.USD,
            inputs.book.as_of,
            DayCount.ACT_365_FIXED,
            InterpolationKind.LOG_LINEAR,
            ExtrapolationPolicy.ERROR,
            BootstrapSettings(),
        ),
        Operation.CALIBRATION: calibration(),
        Operation.TRADE: TradeCommand(record.instrument, market),
        Operation.PORTFOLIO: PortfolioCommand(inputs.book, market, inputs.run, inputs.accounts),
        Operation.SIMULATION: SimulationCommand(
            inputs.request,
            TerminalObservable("synthetic-terminal-fx", "USD/EUR", 2),
            inputs.run,
            0.95,
        ),
        Operation.EXPOSURE: ExposureCommand(
            inputs.request,
            inputs.book,
            inputs.markets,
            inputs.run,
            inputs.accounts,
            inputs.credit,
            (0.95, 0.99),
        ),
        Operation.XVA: XvaCommand(inputs),
        Operation.CAPITAL: CapitalCommand(
            request,
            inputs.book,
            markets,
            inputs.run,
            SupervisoryParameters(
                "Research defaults with explicit synthetic scope; see CCR limitations"
            ),
            ComparisonPolicy(
                Currency.USD,
                Money(Decimal(1), Currency.USD),
                0.1,
                1.0,
                0.08,
                "Synthetic illustrative comparison policy",
            ),
            inputs.accounts,
            (margin,),
        ),
        Operation.COMPARISON: ComparisonCommand(inputs, Tolerance(1.0, 0.05), reproduction),
        Operation.CONVERGENCE: ConvergenceCommand(
            (inputs, path_case(inputs, paths * 2)),
            "CVA",
            ConvergenceAxis.PATH_COUNT,
            Tolerance(1.0, 0.1),
            Tolerance(1.0, 0.1),
            reproduction,
            0.95,
        ),
        Operation.INVARIANTS: InvariantsCommand(benchmark, Tolerance(1e-10, 1e-12), reproduction),
        Operation.SENSITIVITY: SensitivityCommand(
            inputs, factor, 0.001, "CVA", Tolerance(0.01, 0.001), reproduction
        ),
        Operation.STRESS: StressCommand(inputs, (scenario,)),
        Operation.UNCERTAINTY: UncertaintyCommand(inputs, "CVA", StreamKey(20261001, 98), 32, 0.95),
        Operation.MUTATION: MutationCommand(
            probes, mutations(), weak_targets, Tolerance(1e-10, 1e-12), reproduction
        ),
        Operation.ADVERSARIAL: AdversarialCommand(inputs, (factor,), spec),
    }
