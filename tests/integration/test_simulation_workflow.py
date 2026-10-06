import json
import subprocess
import sys
import tracemalloc
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from parallax_risk.application.simulation_benchmark import (
    benchmark_batches,
    benchmark_vectorization,
)
from parallax_risk.application.simulation_research import (
    path_count_study,
    variance_reduction_comparison,
)
from parallax_risk.common.canonical import canonical_value
from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.domain.simulation.arrays import FrozenArray
from parallax_risk.domain.simulation.contracts import PathBatch
from parallax_risk.domain.simulation.controls import ControlVariate
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.observables import TerminalOperation
from parallax_risk.domain.simulation.random import SequenceKind, StreamKey
from tests.fixtures.simulation import component, context, request, service, terminal


def test_workflow_replay_and_safe_log_fields():
    workflow, logs = service()
    config = request(paths=128, batch=16)
    first = workflow.run(config, terminal(), context())
    second = workflow.run(config, terminal(), context())
    assert canonical_value(first) == canonical_value(second)
    assert first.estimate.total_paths == 128
    assert first.estimate.independent_units == 128
    assert first.inference_absence_reason is None
    assert [point.paths for point in first.convergence] == list(range(16, 129, 16))
    for line in logs.getvalue().splitlines():
        event = json.loads(line)
        assert set(event) <= {"event", "run_id", "outcome", "error_type", "level", "timestamp"}
    changed_identity = replace(context(), run_id=type(context().run_id)("different-run"))
    third = workflow.run(config, terminal(), changed_identity)
    assert first.estimate == third.estimate


def test_synthetic_simulation_demo_is_byte_replayable():
    root = Path(__file__).resolve().parents[2]
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [sys.executable, str(root / "scripts/demo_simulation.py")],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
            timeout=60,
        )
        report = json.loads(completed.stdout)
        assert report["project"] == "Parallax Risk" and report["is_synthetic"]
        assert report["convergence"]["sobol_inference"]["estimate"]["independent_units"] == 16
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


def test_antithetic_workflow_counts_pairs_and_sobol_has_no_iid_interval():
    workflow, _ = service()
    result = workflow.run(request(paths=128, batch=16, antithetic=True), terminal(), context())
    assert result.estimate.sampling_unit == "antithetic_pair"
    assert result.estimate.independent_units == 64
    config = request(paths=128, batch=16, kind=SequenceKind.SOBOL)
    single = workflow.run(config, terminal(), context())
    assert single.estimate is None
    assert "no IID" in single.inference_absence_reason
    assert all(point.standard_error is None for point in single.convergence)
    replicated = workflow.replicated_sobol(config, terminal(), context(), replicates=4)
    assert replicated.estimate.independent_units == 4
    assert replicated.estimate.total_paths == 512
    assert len({result.metadata.sequence.key for result in replicated.designs}) == 4
    assert replicated.estimate.standard_error == pytest.approx(
        np.std([result.raw_mean for result in replicated.designs], ddof=1) / 2
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {"context": context(1)},
        {"confidence": 0},
        {"confidence": np.inf},
        {"control": ControlVariate(1, 100, StreamKey(4), 4, "spot")},
        {"control_observable": terminal()},
        {
            "control": ControlVariate(1, 100, request().sequence.key, 4, "spot"),
            "control_observable": terminal(),
        },
    ],
)
def test_workflow_failures_are_explicit_and_logged(arguments):
    workflow, logs = service()
    settings = {"request": request(), "observable": terminal(), "context": context()} | arguments
    with pytest.raises((SimulationError, NumericalError)):
        workflow.run(**settings)
    assert json.loads(logs.getvalue().splitlines()[-1])["outcome"] == "failed"


def test_engine_protocol_checks_contiguity_observation_count_and_completion():
    class BadEngine(MonteCarloEngine):
        def __init__(self, mode):
            self.mode = mode

        def iter_batches(self, config):
            batch = next(super().iter_batches(config))
            if self.mode == "gap":
                yield replace(batch, start_path=1)
            else:
                yield batch

    for mode in ("gap", "incomplete"):
        workflow, _ = service(BadEngine(mode))
        with pytest.raises(SimulationError):
            workflow.run(request(paths=32, batch=16), terminal(), context())

    class WrongCount:
        name, unit, hash = "bad", "units", "f" * 64

        def __call__(self, batch):
            return np.asarray([1.0])

    workflow, _ = service()
    with pytest.raises(SimulationError):
        workflow.run(request(paths=32), WrongCount(), context())


@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "log"},
        {"operation": TerminalOperation.CALL},
        {"strike": 1},
        {"state_index": -1},
        {"multiplier": np.nan},
    ],
)
def test_observable_guards(changes):
    with pytest.raises((SimulationError, NumericalError)):
        replace(terminal(), **changes)


def test_observable_domain_and_all_transformations():
    values = FrozenArray.from_array(np.asarray([[[2.0]], [[4.0]]]))
    batch = PathBatch(0, values, 0)
    assert np.array_equal(replace(terminal(), operation=TerminalOperation.SQUARE)(batch), [4, 16])
    assert np.allclose(replace(terminal(), operation=TerminalOperation.LOG)(batch), np.log([2, 4]))
    call = replace(terminal(), operation=TerminalOperation.CALL, strike=3, multiplier=2)
    assert np.array_equal(call(batch), [0, 2])
    with pytest.raises(SimulationError):
        replace(terminal(), state_index=1)(batch)
    negative = PathBatch(0, FrozenArray.from_array(np.asarray([[[-1.0]]])), 0)
    with pytest.raises(NumericalError):
        replace(terminal(), operation=TerminalOperation.LOG)(negative)
    big = PathBatch(0, FrozenArray.from_array(np.asarray([[[1e308]]])), 0)
    with pytest.raises(NumericalError):
        replace(terminal(), operation=TerminalOperation.SQUARE)(big)


def test_benchmark_measures_buffers_replay_and_does_not_leave_tracing():
    config = request(paths=32, batch=8)
    result = benchmark_batches(MonteCarloEngine(), config, repeats=2)
    assert result.maximum_published_batch_bytes == 8 * 3 * 8
    assert result.equivalent_full_path_buffer_bytes == 32 * 3 * 8
    assert result.traced_peak_bytes >= result.maximum_published_batch_bytes
    assert result.median_seconds > 0 and result.paths_per_second > 0
    assert len(result.elapsed_seconds) == 2
    assert not tracemalloc.is_tracing()
    with pytest.raises(SimulationError):
        benchmark_batches(MonteCarloEngine(), config, repeats=0)
    tracemalloc.start()
    try:
        with pytest.raises(SimulationError, match="existing tracing"):
            benchmark_batches(MonteCarloEngine(), config)
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()
    vector = benchmark_vectorization(component(), paths=16, dt=0.1, key=StreamKey(3))
    assert vector.maximum_absolute_difference < 1e-10
    assert vector.scalar_seconds > 0 and vector.vectorized_seconds > 0


def test_replicated_design_guards():
    workflow, _ = service()
    with pytest.raises(SimulationError):
        workflow.replicated_sobol(request(), terminal(), context(), replicates=4)
    config = request(kind=SequenceKind.SOBOL)
    with pytest.raises(SimulationError):
        workflow.replicated_sobol(config, terminal(), context(), replicates=1)
    config = replace(
        config, sequence=replace(config.sequence, key=StreamKey(20251001, substream=2**32 - 1))
    )
    with pytest.raises(SimulationError):
        workflow.replicated_sobol(config, terminal(), context(), replicates=2)


@pytest.mark.parametrize("counts", [[], (32,), (32, 16), (0, 32), (16, 16)])
def test_study_requires_valid_increasing_path_counts(counts):
    workflow, _ = service()
    with pytest.raises(SimulationError):
        path_count_study(
            workflow,
            request(),
            terminal(),
            context(),
            path_counts=counts,
            replicates=2,
            reference=100,
        )


def test_zero_error_study_reports_slope_absence():
    workflow, _ = service()
    zero = replace(terminal(), multiplier=0)
    study = path_count_study(
        workflow,
        request(paths=32),
        zero,
        context(),
        path_counts=(16, 32),
        replicates=2,
        reference=0,
    )
    assert study.log_rmse_slope is None
    assert "Zero" in study.slope_absence_reason


def test_convergence_range_failures_are_typed():
    from parallax_risk.application.simulation_examples import convergence_experiment

    with pytest.raises(SimulationError):
        convergence_experiment(counts=())
    workflow, _ = service()
    with pytest.raises(NumericalError, match="overflowed"):
        path_count_study(
            workflow,
            request(paths=32),
            terminal(),
            context(),
            path_counts=(16, 32),
            replicates=2,
            reference=1e308,
        )


def test_batch_benchmark_rejects_incomplete_and_nonreplayable_engines():
    class FaultyEngine(MonteCarloEngine):
        def __init__(self, mode):
            self.mode, self.iteration = mode, 0

        def iter_batches(self, config):
            self.iteration += 1
            for batch in super().iter_batches(config):
                if self.mode == "incomplete":
                    return
                yield replace(
                    batch, values=FrozenArray.from_array(batch.values.array + self.iteration)
                )

    for mode in ("incomplete", "changed"):
        with pytest.raises(SimulationError):
            benchmark_batches(FaultyEngine(mode), request(paths=8, batch=4), repeats=2)
        assert not tracemalloc.is_tracing()


@pytest.mark.parametrize(
    "changes",
    [
        {"request": request(kind=SequenceKind.SOBOL)},
        {"request": request(antithetic=True)},
        {"request": request(paths=3)},
        {"request": request(batch=3)},
        {"pilot_key": request().sequence.key},
        {"pilot_key": StreamKey(1)},
        {"pilot_paths": 1},
    ],
)
def test_variance_comparison_checks_pilot_and_equal_work_assumptions(changes):
    workflow, _ = service()
    arguments = {
        "service": workflow,
        "request": request(),
        "target": terminal(),
        "control_observable": terminal(),
        "context": context(),
        "known_control_mean": 100,
        "pilot_key": StreamKey(20251001, 1),
        "pilot_paths": 16,
    } | changes
    with pytest.raises(SimulationError):
        variance_reduction_comparison(**arguments)
