"""Versioned service commands and injected numerical workflows; no HTTP or database."""

import math
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from enum import StrEnum

from parallax_risk.application.calibration import CalibrationService
from parallax_risk.application.ccr import CcrService, ScopeMargin
from parallax_risk.application.context import RunContext
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.simulation import SimulationService
from parallax_risk.application.validation import ValidationLab
from parallax_risk.application.validation_invariants import cva_invariants
from parallax_risk.application.validation_models import ProductionCvaModel, ProductionXvaModel
from parallax_risk.application.validation_mutation import campaign
from parallax_risk.application.validation_probes import OperationProbeModel, ProbeCase, probe_suite
from parallax_risk.application.validation_search import SearchOptimizer, search
from parallax_risk.application.validation_search_models import (
    IndependentCreditCvaChallenger,
    XvaCvaProduction,
    XvaSearchCases,
)
from parallax_risk.application.validation_stress import StressScenario, factor_unit, stress
from parallax_risk.application.wire import decode
from parallax_risk.application.xva_revaluation import XvaExperiment, XvaRevaluation
from parallax_risk.common.canonical import JsonValue
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CalibrationRunId, CurveId
from parallax_risk.domain.calibration.contracts import CalibrationSettings, ParameterBound
from parallax_risk.domain.calibration.problems import (
    HestonCallProblem,
    HullWhiteBondOptionProblem,
    VasicekBondProblem,
)
from parallax_risk.domain.ccr.contracts import ComparisonPolicy, SupervisoryParameters
from parallax_risk.domain.exposure.contracts import CreditScenario
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario
from parallax_risk.domain.market.curves.bootstrap import (
    BootstrapSettings,
    DepositQuote,
    ParSwapQuote,
    bootstrap_discount_curve,
)
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.portfolio.collateral import CollateralAccount
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.pricing.engine import DiscountingEngine, Instrument, PricingContext
from parallax_risk.domain.simulation.contracts import SimulationRequest
from parallax_risk.domain.simulation.observables import TerminalObservable
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.benchmark import (
    CvaBenchmarkCase,
    FlatHazardProbabilityProblem,
    IndependentCvaBenchmark,
)
from parallax_risk.domain.validation.checks import ConvergenceAxis, sensitivity
from parallax_risk.domain.validation.contracts import Metric, Tolerance
from parallax_risk.domain.validation.mutation import Mutation
from parallax_risk.domain.validation.search import SearchSpec
from parallax_risk.domain.validation.uncertainty import IidUnitResampler, bootstrap
from parallax_risk.domain.xva.risk import RiskFactor


class Operation(StrEnum):
    CURVE = "market/curves"
    CALIBRATION = "market/calibrations"
    TRADE = "pricing/trades"
    PORTFOLIO = "pricing/portfolios"
    SIMULATION = "simulation"
    EXPOSURE = "exposure"
    XVA = "xva"
    CAPITAL = "capital"
    COMPARISON = "validation/comparison"
    CONVERGENCE = "validation/convergence"
    INVARIANTS = "validation/invariants"
    SENSITIVITY = "validation/sensitivity"
    STRESS = "validation/stress"
    UNCERTAINTY = "validation/uncertainty"
    MUTATION = "validation/mutation"
    ADVERSARIAL = "validation/adversarial"


@dataclass(frozen=True, slots=True)
class CurveCommand:
    quotes: tuple[DepositQuote | ParSwapQuote, ...]
    curve_id: CurveId
    currency: Currency
    valuation_date: date
    curve_day_count: DayCount
    interpolation: InterpolationKind
    extrapolation: ExtrapolationPolicy
    settings: BootstrapSettings


@dataclass(frozen=True, slots=True)
class CalibrationCommand:
    problem: (
        VasicekBondProblem
        | HullWhiteBondOptionProblem
        | HestonCallProblem
        | FlatHazardProbabilityProblem
    )
    bounds: tuple[ParameterBound, ...]
    settings: CalibrationSettings
    calibration_id: CalibrationRunId
    run: RunContext


@dataclass(frozen=True, slots=True)
class TradeCommand:
    instrument: Instrument
    market: PricingContext


@dataclass(frozen=True, slots=True)
class PortfolioCommand:
    book: PortfolioSnapshot
    market: PricingContext
    run: RunContext
    accounts: tuple[CollateralAccount, ...]


@dataclass(frozen=True, slots=True)
class SimulationCommand:
    request: SimulationRequest
    observable: TerminalObservable
    run: RunContext
    confidence: float


@dataclass(frozen=True, slots=True)
class ExposureCommand:
    request: SimulationRequest
    book: PortfolioSnapshot
    markets: ConditionalMarketScenario
    run: RunContext
    accounts: tuple[CollateralAccount, ...]
    credit: tuple[CreditScenario, ...]
    quantiles: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class XvaCommand:
    experiment: XvaExperiment


@dataclass(frozen=True, slots=True)
class CapitalCommand:
    request: SimulationRequest
    book: PortfolioSnapshot
    markets: ConditionalMarketScenario
    run: RunContext
    parameters: SupervisoryParameters
    policy: ComparisonPolicy
    accounts: tuple[CollateralAccount, ...]
    margins: tuple[ScopeMargin, ...]


@dataclass(frozen=True, slots=True)
class ComparisonCommand:
    case: CvaBenchmarkCase | XvaExperiment
    tolerance: Tolerance
    reproduction: str


@dataclass(frozen=True, slots=True)
class ConvergenceCommand:
    cases: tuple[XvaExperiment, ...]
    metric: str
    axis: ConvergenceAxis
    stability: Tolerance
    precision: Tolerance
    reproduction: str
    confidence: float


@dataclass(frozen=True, slots=True)
class InvariantsCommand:
    case: CvaBenchmarkCase
    tolerance: Tolerance
    reproduction: str


@dataclass(frozen=True, slots=True)
class SensitivityCommand:
    experiment: XvaExperiment
    factor: RiskFactor
    bump: float
    metric: str
    tolerance: Tolerance
    reproduction: str


@dataclass(frozen=True, slots=True)
class StressCommand:
    experiment: XvaExperiment
    scenarios: tuple[StressScenario, ...]


@dataclass(frozen=True, slots=True)
class UncertaintyCommand:
    experiment: XvaExperiment
    metric: str
    key: StreamKey
    replicates: int
    confidence: float


@dataclass(frozen=True, slots=True)
class MutationCommand:
    case: ProbeCase
    mutations: tuple[Mutation, ...]
    targets: tuple[Metric, ...]
    tolerance: Tolerance
    reproduction: str


@dataclass(frozen=True, slots=True)
class AdversarialCommand:
    experiment: XvaExperiment
    factors: tuple[RiskFactor, ...]
    specification: SearchSpec


type Command = (
    CurveCommand
    | CalibrationCommand
    | TradeCommand
    | PortfolioCommand
    | SimulationCommand
    | ExposureCommand
    | XvaCommand
    | CapitalCommand
    | ComparisonCommand
    | ConvergenceCommand
    | InvariantsCommand
    | SensitivityCommand
    | StressCommand
    | UncertaintyCommand
    | MutationCommand
    | AdversarialCommand
)

COMMANDS: dict[Operation, type[Command]] = dict(
    zip(
        Operation,
        (
            CurveCommand,
            CalibrationCommand,
            TradeCommand,
            PortfolioCommand,
            SimulationCommand,
            ExposureCommand,
            XvaCommand,
            CapitalCommand,
            ComparisonCommand,
            ConvergenceCommand,
            InvariantsCommand,
            SensitivityCommand,
            StressCommand,
            UncertaintyCommand,
            MutationCommand,
            AdversarialCommand,
        ),
        strict=True,
    )
)


def walk(item: object) -> tuple[object, ...]:
    """Inspect trusted immutable inputs, deduplicating repeated scenario bindings."""
    found: list[object] = []
    seen: set[int] = set()
    stack = [item]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        found.append(current)
        if is_dataclass(current) and not isinstance(current, type):
            stack.extend(getattr(current, f.name) for f in fields(current) if f.init)
        elif isinstance(current, tuple):
            stack.extend(current)
    return tuple(found)


@dataclass(frozen=True, slots=True)
class WorkLimits:
    """Conservative declared admission budgets, not measured memory/latency promises."""

    maximum_paths: int = 16384
    maximum_trades: int = 2000
    maximum_steps: int = 512
    maximum_work: int = 2_000_000
    maximum_output_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        for limit in (
            self.maximum_paths,
            self.maximum_trades,
            self.maximum_steps,
            self.maximum_work,
            self.maximum_output_bytes,
        ):
            if type(limit) is not int or limit <= 0:
                raise DomainValidationError("Work limits must be positive integers")

    def validate(self, command: Command) -> None:
        nodes = walk(command)
        requests = [x for x in nodes if isinstance(x, SimulationRequest)]
        books = [x for x in nodes if isinstance(x, PortfolioSnapshot)]
        trades = max(
            (sum(len(n.trades) for c in b.counterparties for n in c.netting_sets) for b in books),
            default=1,
        )
        if trades > self.maximum_trades or any(
            r.path_count > self.maximum_paths or r.grid.steps > self.maximum_steps for r in requests
        ):
            raise DomainValidationError(
                "Service input exceeds path/trade/time-step admission limits"
            )
        if any(
            r.driver_dimension > 16
            or r.state_dimension > 16
            or 8
            * min(r.batch_size, r.path_count)
            * (len(r.grid.times) * r.state_dimension + 5 * r.grid.steps * r.driver_dimension)
            > self.maximum_output_bytes
            for r in requests
        ):
            raise DomainValidationError("Service factor/batch-buffer admission budget exceeded")
        multiplier = 1
        if isinstance(command, AdversarialCommand):
            if command.specification.maximum_evaluations > 64:
                raise DomainValidationError("Service search evaluation limit is 64")
            multiplier = 2 * command.specification.maximum_evaluations
        elif isinstance(command, SensitivityCommand):
            multiplier = 5
        elif isinstance(command, StressCommand):
            if len(command.scenarios) > 16:
                raise DomainValidationError("Service stress scenario limit is 16")
            multiplier = len(command.scenarios) + 1
        elif isinstance(command, ConvergenceCommand) and len(command.cases) > 16:
            raise DomainValidationError("Service convergence case limit is 16")
        elif isinstance(command, CalibrationCommand):
            count = (
                len(command.problem.observed)
                if isinstance(command.problem, FlatHazardProbabilityProblem)
                else len(command.problem.observations)
            )
            quadrature = (
                command.problem.fourier_settings.subdivision_limit
                if isinstance(command.problem, HestonCallProblem)
                else 1
            )
            if (
                command.settings.max_evaluations > 1000
                or count > 64
                or count * command.settings.max_evaluations * quadrature > self.maximum_work
            ):
                raise DomainValidationError("Service calibration admission budget exceeded")
        elif isinstance(command, UncertaintyCommand) and not 2 <= command.replicates <= 1000:
            raise DomainValidationError("Service bootstrap replicate limit is 1000")
        elif isinstance(command, MutationCommand) and len(command.mutations) > 32:
            raise DomainValidationError("Service mutation limit is 32")
        work = sum(r.path_count * len(r.grid.times) for r in requests) * trades * multiplier
        collateral_scopes = max(
            (
                sum(n.csa is not None for c in b.counterparties for n in c.netting_sets)
                for b in books
            ),
            default=0,
        )
        work += (
            sum(r.path_count * len(r.grid.times) ** 2 for r in requests)
            * collateral_scopes
            * multiplier
        )
        if work > self.maximum_work:
            raise DomainValidationError("Service path/time/trade/evaluation work budget exceeded")


@dataclass(frozen=True, slots=True)
class Workflows:
    pricing: DiscountingEngine
    portfolio: PortfolioService
    calibration: CalibrationService
    simulation: SimulationService
    exposure: ExposureService
    xva: XvaRevaluation
    capital: CcrService
    optimizer: SearchOptimizer
    limits: WorkLimits = WorkLimits()

    def prepare(self, operation: Operation, payload: JsonValue) -> Command:
        command = decode(payload, COMMANDS[operation])
        self.limits.validate(command)
        return command

    def execute(self, command: Command) -> object:
        self.limits.validate(command)
        model = ProductionXvaModel(self.xva)
        match command:
            case CurveCommand():
                return bootstrap_discount_curve(
                    command.quotes,
                    curve_id=command.curve_id,
                    currency=command.currency,
                    valuation_date=command.valuation_date,
                    curve_day_count=command.curve_day_count,
                    interpolation=command.interpolation,
                    extrapolation=command.extrapolation,
                    settings=command.settings,
                )
            case CalibrationCommand():
                return self.calibration.calibrate(
                    command.problem,
                    command.bounds,
                    command.settings,
                    command.calibration_id,
                    command.run,
                )
            case TradeCommand():
                return self.pricing.price(command.instrument, command.market)
            case PortfolioCommand():
                return self.portfolio.value(
                    command.book, command.market, command.run, command.accounts
                )
            case SimulationCommand():
                return self.simulation.run(
                    command.request, command.observable, command.run, confidence=command.confidence
                )
            case ExposureCommand():
                return self.exposure.run(
                    command.request,
                    command.book,
                    command.markets,
                    command.run,
                    accounts=command.accounts,
                    credit=command.credit,
                    quantiles=command.quantiles,
                    maximum_output_bytes=self.limits.maximum_output_bytes,
                )
            case XvaCommand():
                return self.xva.value(command.experiment)
            case CapitalCommand():
                return self.capital.run(
                    command.request,
                    command.book,
                    command.markets,
                    command.run,
                    command.parameters,
                    command.policy,
                    accounts=command.accounts,
                    margins=command.margins,
                    maximum_output_bytes=self.limits.maximum_output_bytes,
                )
            case ComparisonCommand():
                if isinstance(command.case, CvaBenchmarkCase):
                    return ValidationLab(ProductionCvaModel(), IndependentCvaBenchmark()).compare(
                        command.case, command.tolerance, command.reproduction
                    )
                return ValidationLab(
                    XvaCvaProduction(model), IndependentCreditCvaChallenger(self.xva)
                ).compare(command.case, command.tolerance, command.reproduction)
            case ConvergenceCommand():
                return model.convergence(
                    command.cases,
                    command.metric,
                    command.axis,
                    command.stability,
                    command.precision,
                    command.reproduction,
                    confidence=command.confidence,
                    maximum_evaluations=16,
                )
            case InvariantsCommand():
                return cva_invariants(
                    ProductionCvaModel(), command.case, command.tolerance, command.reproduction
                )
            case SensitivityCommand():
                return sensitivity(
                    lambda a: model.evaluate(
                        self.xva.bump(command.experiment, command.factor, a)
                    ).metric(command.metric),
                    command.bump,
                    factor_unit(command.factor),
                    command.tolerance,
                    evidence=(command.experiment.hash,),
                    reproduction=command.reproduction,
                    version="0.7.0",
                )
            case StressCommand():
                return stress(model, command.experiment, command.scenarios, maximum_evaluations=16)
            case UncertaintyCommand():
                return bootstrap(
                    model.observations(command.experiment, command.metric),
                    command.key,
                    IidUnitResampler(),
                    lambda xs: math.fsum(xs) / len(xs),
                    statistic_name="mean",
                    replicates=command.replicates,
                    confidence=command.confidence,
                )
            case MutationCommand():
                return campaign(
                    OperationProbeModel(),
                    command.case,
                    command.mutations,
                    lambda o: probe_suite(o, command.targets, command.tolerance),
                    command.reproduction,
                    maximum_evaluations=33,
                )
            case AdversarialCommand():
                build = XvaSearchCases(
                    self.xva, command.experiment, command.factors, command.specification.dimensions
                )
                return search(
                    XvaCvaProduction(model),
                    IndependentCreditCvaChallenger(self.xva),
                    build,
                    self.optimizer,
                    command.specification,
                )
