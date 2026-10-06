"""Measured batch memory and scalar/vectorized checks; no timing performance gates."""

import hashlib
import statistics
import time
import tracemalloc
from dataclasses import dataclass

import numpy as np

from parallax_risk.application.simulation import SimulationEngine
from parallax_risk.common.errors import SimulationError
from parallax_risk.domain.models.base import Discretization
from parallax_risk.domain.models.discretization import (
    EulerMaruyama,
    ExactTransition,
    HestonProjectedEuler,
)
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.contracts import ProcessComponent, Scheme, SimulationRequest
from parallax_risk.domain.simulation.kernels import step_batch
from parallax_risk.domain.simulation.random import NormalStream, SequenceSpec, StreamKey


@dataclass(frozen=True, slots=True)
class BatchBenchmark:
    request_hash: str
    metadata_hash: str
    elapsed_seconds: tuple[float, ...]
    median_seconds: float
    traced_peak_bytes: int
    maximum_published_batch_bytes: int
    equivalent_full_path_buffer_bytes: int
    paths_per_second: float
    output_buffer_sha256: str
    memory_scope: str = "tracemalloc peak (tracked Python/NumPy allocations), not process RSS"
    operation: str = "complete streaming path generation, immutable publication and SHA256"


def benchmark_batches(
    engine: SimulationEngine, request: SimulationRequest, *, repeats: int = 3
) -> BatchBenchmark:
    from parallax_risk.common.canonical import content_hash

    integer(repeats, "benchmark repetitions")
    if tracemalloc.is_tracing():
        raise SimulationError("Benchmark must own its tracing session; existing tracing is active")
    # Warm exactly the workload, using a fresh deterministic iteration.
    for warm_batch in engine.iter_batches(request):
        del warm_batch
    timings, peak, maximum = [], 0, 0
    previous_digest: str | None = None
    for _ in range(repeats):
        digest = hashlib.sha256()
        tracemalloc.start()
        started = time.perf_counter()
        try:
            produced = 0
            for batch in engine.iter_batches(request):
                produced += batch.path_count
                maximum = max(maximum, batch.values.nbytes)
                digest.update(batch.values.payload)
            elapsed = time.perf_counter() - started
            peak = max(peak, tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
        if produced != request.path_count or elapsed <= 0:
            raise SimulationError("Benchmark workload did not produce the complete design")
        observed = digest.hexdigest()
        if previous_digest is not None and observed != previous_digest:
            raise SimulationError("Benchmark repetitions failed exact output replay")
        previous_digest = observed
        timings.append(elapsed)
    assert previous_digest is not None
    median = statistics.median(timings)
    full = request.path_count * len(request.grid.times) * request.state_dimension * 8
    return BatchBenchmark(
        request.hash,
        content_hash(engine.metadata(request)),
        tuple(timings),
        median,
        peak,
        maximum,
        full,
        request.path_count / median,
        previous_digest,
    )


@dataclass(frozen=True, slots=True)
class VectorizationBenchmark:
    component_name: str
    path_count: int
    scalar_seconds: float
    vectorized_seconds: float
    measured_speed_ratio: float
    maximum_absolute_difference: float
    absolute_tolerance: float = 1e-12
    relative_tolerance: float = 1e-12


def benchmark_vectorization(
    component: ProcessComponent, *, paths: int, dt: float, key: StreamKey
) -> VectorizationBenchmark:
    integer(paths, "vectorization benchmark paths")
    shocks = NormalStream(SequenceSpec(key), component.process.driver_dimension, paths).draw(paths)
    states = np.tile(np.asarray(component.initial_state, dtype=np.float64), (paths, 1))
    strategies: dict[Scheme, Discretization] = {
        Scheme.EXACT: ExactTransition(),
        Scheme.EULER: EulerMaruyama(),
        Scheme.HESTON_PROJECTED: HestonProjectedEuler(),
    }
    strategy = strategies[component.scheme]
    started = time.perf_counter()
    reference = np.asarray(
        [
            strategy.step(
                component.process, 0.0, component.initial_state, dt, tuple(float(x) for x in row)
            )
            for row in shocks
        ],
        dtype=np.float64,
    )
    scalar_seconds = time.perf_counter() - started
    started = time.perf_counter()
    vectorized, _ = step_batch(component, 0.0, states, dt, shocks)
    vector_seconds = time.perf_counter() - started
    difference = float(np.max(np.abs(reference - vectorized)))
    if not np.allclose(reference, vectorized, atol=1e-12, rtol=1e-12):
        raise SimulationError("Scalar/vectorized transition reconciliation exceeded tolerance")
    if scalar_seconds <= 0 or vector_seconds <= 0:
        raise SimulationError("Benchmark clock resolution cannot measure this workload")
    return VectorizationBenchmark(
        component.name,
        paths,
        scalar_seconds,
        vector_seconds,
        scalar_seconds / vector_seconds,
        difference,
    )
