"""Measure the local Phase 4 workload; timings are evidence, not replayable numbers."""

import json
from dataclasses import replace

from parallax_risk.application.simulation_benchmark import (
    benchmark_batches,
    benchmark_vectorization,
)
from parallax_risk.application.simulation_examples import synthetic_inputs
from parallax_risk.common.canonical import canonical_value
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import StreamKey


def main() -> None:
    request, _ = synthetic_inputs(paths=65536)
    request = replace(request, grid=TimeGrid(tuple(index / 32 for index in range(33))))
    engine = MonteCarloEngine()
    reports = [benchmark_batches(engine, replace(request, batch_size=size)) for size in (512, 4096)]
    vector = benchmark_vectorization(
        request.components[0], paths=8192, dt=1 / 32, key=StreamKey(20251001)
    )
    print(
        json.dumps(
            {
                "project": "Parallax Risk",
                "is_synthetic": True,
                "batch_benchmarks": canonical_value(tuple(reports)),
                "vectorization": canonical_value(vector),
                "environment": canonical_value(engine.metadata(request)),
            },
            indent=2,
            allow_nan=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
