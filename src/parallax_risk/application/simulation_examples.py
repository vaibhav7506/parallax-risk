"""Explicit synthetic Phase 4 experiments; notebooks only call these production functions."""

import io
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from parallax_risk.application.context import RunContext
from parallax_risk.application.simulation import (
    ReplicatedSobolResult,
    SimulationRunResult,
    SimulationService,
)
from parallax_risk.application.simulation_research import (
    PathCountStudy,
    VarianceReductionComparison,
    path_count_study,
    variance_reduction_comparison,
)
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import SimulationError
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.rates import Vasicek
from parallax_risk.domain.simulation.analytics import gbm_call_expectation, gbm_terminal_moments
from parallax_risk.domain.simulation.contracts import (
    ProcessComponent,
    Scheme,
    SimulationRequest,
    TimeGrid,
)
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.observables import TerminalObservable, TerminalOperation
from parallax_risk.domain.simulation.random import SequenceKind, SequenceSpec, StreamKey


def synthetic_inputs(
    *, paths: int = 8192, batch: int = 1024
) -> tuple[SimulationRequest, RunContext]:
    model = GeometricBrownianMotion(0.05, 0.2)
    component = ProcessComponent(
        "asset", model, (100.0,), Scheme.EXACT, ("USD/underlying_unit",), "Q"
    )
    key = StreamKey(20251001)
    request = SimulationRequest((component,), TimeGrid((0.0, 1.0)), paths, batch, SequenceSpec(key))
    context = RunContext(
        RiskRunId("synthetic-phase4"),
        datetime(2025, 1, 1, tzinfo=UTC),
        key.seed,
        content_hash(
            {"experiment": "synthetic_phase4_v1", "configuration_source": "explicit_no_environment"}
        ),
    )
    return request, context


def _service() -> SimulationService:
    return SimulationService(MonteCarloEngine(), create_logger(stream=io.StringIO()))


@dataclass(frozen=True, slots=True)
class MomentExperiment:
    gbm_reference_mean: float
    gbm_reference_variance: float
    gbm: SimulationRunResult
    vasicek_reference_mean: float
    vasicek_reference_variance: float
    vasicek: SimulationRunResult
    is_synthetic: bool = True


def moment_experiment(*, paths: int = 65536) -> MomentExperiment:
    request, context = synthetic_inputs(paths=paths)
    gbm_model = GeometricBrownianMotion(0.05, 0.2)
    rate_model = Vasicek(0.4, 0.05, 0.02)
    rate = ProcessComponent("rate", rate_model, (0.03,), Scheme.EXACT, ("decimal/year",), "Q")
    workflow = _service()
    gbm = workflow.run(
        request, TerminalObservable("gbm_terminal", "USD/underlying_unit", 0), context
    )
    vasicek = workflow.run(
        replace(request, components=(rate,)),
        TerminalObservable("rate_terminal", "decimal/year", 0),
        context,
    )
    mean, variance = gbm_terminal_moments(gbm_model, 100.0, 1.0)
    rate_mean, rate_variance = rate_model.moments(0.03, 1.0)
    return MomentExperiment(mean, variance, gbm, rate_mean, rate_variance, vasicek)


def variance_experiment(
    *, paths: int = 8192, pilot_paths: int = 2048
) -> VarianceReductionComparison:
    request, context = synthetic_inputs(paths=paths)
    target = TerminalObservable(
        "terminal_call_statistic", "USD/underlying_unit", 0, TerminalOperation.CALL, 100.0
    )
    control = TerminalObservable("terminal_spot", "USD/underlying_unit", 0)
    mean, _ = gbm_terminal_moments(GeometricBrownianMotion(0.05, 0.2), 100.0, 1.0)
    return variance_reduction_comparison(
        _service(),
        request,
        target,
        control,
        context,
        known_control_mean=mean,
        pilot_key=StreamKey(context.seed, stream=1),
        pilot_paths=pilot_paths,
    )


@dataclass(frozen=True, slots=True)
class ConvergenceExperiment:
    reference_call_expectation: float
    pseudo: PathCountStudy
    sobol: PathCountStudy
    sobol_inference: ReplicatedSobolResult
    is_synthetic: bool = True


def convergence_experiment(
    *, counts: tuple[int, ...] = (256, 1024, 4096, 16384), replicates: int = 16
) -> ConvergenceExperiment:
    if not isinstance(counts, tuple) or len(counts) < 2:
        raise SimulationError("Convergence example requires at least two immutable path counts")
    request, context = synthetic_inputs(paths=counts[-1])
    target = TerminalObservable(
        "terminal_call_statistic", "USD/underlying_unit", 0, TerminalOperation.CALL, 100.0
    )
    reference = gbm_call_expectation(GeometricBrownianMotion(0.05, 0.2), 100, 1, 100)
    workflow = _service()
    pseudo = path_count_study(
        workflow,
        request,
        target,
        context,
        path_counts=counts,
        replicates=replicates,
        reference=reference,
    )
    sobol_request = replace(request, sequence=replace(request.sequence, kind=SequenceKind.SOBOL))
    sobol = path_count_study(
        workflow,
        sobol_request,
        target,
        context,
        path_counts=counts,
        replicates=replicates,
        reference=reference,
    )
    inference = workflow.replicated_sobol(sobol_request, target, context, replicates=replicates)
    return ConvergenceExperiment(reference, pseudo, sobol, inference)
