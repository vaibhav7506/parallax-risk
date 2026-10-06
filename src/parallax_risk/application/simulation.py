"""Injected research workflow: provenance, descriptive moments and valid sampling units."""

from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Protocol

import numpy as np

from parallax_risk.application.context import RunContext
from parallax_risk.common.errors import ParallaxError, SimulationError
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.common.math import require_finite
from parallax_risk.domain.simulation.arrays import finite_array, integer
from parallax_risk.domain.simulation.contracts import (
    PathBatch,
    SimulationMetadata,
    SimulationRequest,
)
from parallax_risk.domain.simulation.controls import ControlVariate
from parallax_risk.domain.simulation.observables import PathObservable
from parallax_risk.domain.simulation.random import SequenceKind
from parallax_risk.domain.simulation.statistics import (
    Estimate,
    OnlineMoments,
    independent_scramble_estimate,
    sampling_units,
)


class SimulationEngine(Protocol):
    def metadata(
        self, request: SimulationRequest, *, source_revision: str | None = None
    ) -> SimulationMetadata: ...

    def iter_batches(self, request: SimulationRequest) -> Iterator[PathBatch]: ...


@dataclass(frozen=True, slots=True)
class ConvergencePoint:
    paths: int
    mean: float
    standard_error: float | None


@dataclass(frozen=True, slots=True)
class SimulationRunResult:
    context: RunContext
    metadata: SimulationMetadata
    observable_name: str
    observable_hash: str
    observable_unit: str
    raw_mean: float
    raw_descriptive_variance: float
    estimate: Estimate | None
    inference_absence_reason: str | None
    convergence: tuple[ConvergencePoint, ...]
    variance_projection_count: int
    control: ControlVariate | None
    control_observable_hash: str | None
    confidence: float


@dataclass(frozen=True, slots=True)
class ReplicatedSobolResult:
    context: RunContext
    designs: tuple[SimulationRunResult, ...]
    estimate: Estimate


class SimulationService:
    def __init__(self, engine: SimulationEngine, logger: WorkflowLogger) -> None:
        self.engine, self.logger = engine, logger

    def run(
        self,
        request: SimulationRequest,
        observable: PathObservable,
        context: RunContext,
        *,
        confidence: float = 0.95,
        control: ControlVariate | None = None,
        control_observable: PathObservable | None = None,
        source_revision: str | None = None,
    ) -> SimulationRunResult:
        run_id = str(context.run_id)
        self.logger.event("simulation_started", run_id=run_id, outcome="started")
        try:
            if context.seed != request.sequence.key.seed:
                raise SimulationError("Run context seed must match the simulation root seed")
            confidence = require_finite(confidence, name="confidence")
            if not 0 < confidence < 1:
                raise SimulationError("Confidence must be strictly between zero and one")
            if (control is None) != (control_observable is None):
                raise SimulationError("Control model and observable must be supplied together")
            if control is not None and control.pilot_key == request.sequence.key:
                raise SimulationError("Pilot and evaluation must use distinct explicit streams")
            metadata = self.engine.metadata(request, source_revision=source_revision)
            raw, units = OnlineMoments(), OnlineMoments()
            convergence: list[ConvergencePoint] = []
            projections = 0
            for batch in self.engine.iter_batches(request):
                values = finite_array(observable(batch), ndim=1, name="path observable")
                if values.size != batch.path_count or batch.start_path != raw.count:
                    raise SimulationError(
                        "Engine batches and observable values must be contiguous and aligned"
                    )
                raw.update(values)
                if control is not None and control_observable is not None:
                    values = control.adjust(
                        values, control_observable(batch), evaluation_key=request.sequence.key
                    )
                units.update(sampling_units(values, antithetic=request.sequence.antithetic))
                error = None
                if request.sequence.kind == SequenceKind.PSEUDO and units.count >= 2:
                    error = (units.variance / units.count) ** 0.5
                convergence.append(ConvergencePoint(raw.count, units.mean, error))
                projections += batch.variance_projection_count
            if raw.count != request.path_count:
                raise SimulationError("Engine did not produce the complete configured path design")
            estimate, reason = None, None
            if request.sequence.kind == SequenceKind.SOBOL:
                reason = (
                    "One scrambled Sobol design has no IID standard error; "
                    "use independent scramblings"
                )
            else:
                estimate = units.estimate(
                    total_paths=raw.count,
                    sampling_unit="antithetic_pair" if request.sequence.antithetic else "iid_path",
                    confidence=confidence,
                )
            result = SimulationRunResult(
                context,
                metadata,
                observable.name,
                observable.hash,
                observable.unit,
                raw.mean,
                raw.variance,
                estimate,
                reason,
                tuple(convergence),
                projections,
                control,
                None if control_observable is None else control_observable.hash,
                confidence,
            )
        except ParallaxError as error:
            self.logger.event(
                "simulation_failed",
                run_id=run_id,
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event("simulation_completed", run_id=run_id, outcome="completed")
        return result

    def replicated_sobol(
        self,
        request: SimulationRequest,
        observable: PathObservable,
        context: RunContext,
        *,
        replicates: int,
        confidence: float = 0.95,
        source_revision: str | None = None,
    ) -> ReplicatedSobolResult:
        if request.sequence.kind != SequenceKind.SOBOL:
            raise SimulationError("Independent-scramble inference requires a Sobol design")
        integer(replicates, "independent scramblings", minimum=2)
        key = request.sequence.key
        integer(
            key.substream + replicates - 1, "last scramble substream", minimum=0, maximum=2**32 - 1
        )
        designs = tuple(
            self.run(
                replace(
                    request,
                    sequence=replace(
                        request.sequence, key=replace(key, substream=key.substream + index)
                    ),
                ),
                observable,
                context,
                confidence=confidence,
                source_revision=source_revision,
            )
            for index in range(replicates)
        )
        means = np.asarray([design.convergence[-1].mean for design in designs], dtype=np.float64)
        estimate = independent_scramble_estimate(
            means,
            paths_per_replicate=request.path_count,
            confidence=confidence,
        )
        return ReplicatedSobolResult(context, designs, estimate)
