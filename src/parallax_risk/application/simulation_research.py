"""Production experiment orchestration used by the scripts and research notebooks."""

from dataclasses import dataclass, replace

import numpy as np

from parallax_risk.application.context import RunContext
from parallax_risk.application.simulation import SimulationRunResult, SimulationService
from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.contracts import SimulationRequest
from parallax_risk.domain.simulation.controls import ControlVariate, fit_control
from parallax_risk.domain.simulation.observables import PathObservable
from parallax_risk.domain.simulation.random import SequenceKind, StreamKey


@dataclass(frozen=True, slots=True)
class StudyRow:
    paths_per_replicate: int
    replicate_means: tuple[float, ...]
    reference: float
    root_mean_square_error: float
    bias: float
    empirical_variance_of_replicate_means: float
    total_paths: int


@dataclass(frozen=True, slots=True)
class PathCountStudy:
    kind: SequenceKind
    rows: tuple[StudyRow, ...]
    log_rmse_slope: float | None
    slope_absence_reason: str | None
    nested_prefixes: bool = True
    interpretation: str = (
        "Finite seeded experiment; slope is descriptive, not a convergence guarantee"
    )


def path_count_study(
    service: SimulationService,
    request: SimulationRequest,
    observable: PathObservable,
    context: RunContext,
    *,
    path_counts: tuple[int, ...],
    replicates: int,
    reference: float,
) -> PathCountStudy:
    reference = require_finite(reference, name="analytical reference")
    integer(replicates, "study replicates", minimum=2)
    if not isinstance(path_counts, tuple) or len(path_counts) < 2:
        raise SimulationError("Path-count study requires at least two immutable path counts")
    for count in path_counts:
        integer(count, "study path count", minimum=2)
    if any(right <= left for left, right in zip(path_counts[:-1], path_counts[1:], strict=True)):
        raise SimulationError("Study path counts must be strictly increasing")
    key = request.sequence.key
    integer(key.substream + replicates - 1, "last study substream", minimum=0, maximum=2**32 - 1)
    rows = []
    for count in path_counts:
        means = []
        for index in range(replicates):
            changed = replace(
                request,
                path_count=count,
                sequence=replace(
                    request.sequence, key=replace(key, substream=key.substream + index)
                ),
            )
            result = service.run(changed, observable, context)
            means.append(result.convergence[-1].mean)
        try:
            with np.errstate(over="raise", invalid="raise"):
                errors = np.asarray(means) - reference
                rmse = require_finite(
                    float(np.sqrt(np.mean(errors * errors))), name="empirical RMSE"
                )
                bias = require_finite(float(np.mean(errors)), name="empirical bias")
                variance = require_finite(float(np.var(means, ddof=1)), name="replicate variance")
        except FloatingPointError as error:
            raise NumericalError("Path-count study error moments overflowed") from error
        rows.append(
            StudyRow(count, tuple(means), reference, rmse, bias, variance, count * replicates)
        )
    if any(row.root_mean_square_error == 0 for row in rows):
        slope, reason = None, "Zero observed RMSE has no finite logarithmic slope"
    else:
        slope = require_finite(
            float(
                np.polyfit(
                    np.log(np.asarray(path_counts, dtype=np.float64)),
                    np.log(np.asarray([row.root_mean_square_error for row in rows])),
                    1,
                )[0]
            ),
            name="descriptive convergence slope",
        )
        reason = None
    return PathCountStudy(request.sequence.kind, tuple(rows), slope, reason)


@dataclass(frozen=True, slots=True)
class VarianceReductionCase:
    name: str
    result: SimulationRunResult
    pilot_paths: int
    evaluation_paths: int
    variance_gain_against_plain: float | None
    work_adjusted_gain_against_plain: float | None


@dataclass(frozen=True, slots=True)
class VarianceReductionComparison:
    pilot_control: ControlVariate
    cases: tuple[VarianceReductionCase, ...]
    interpretation: str = (
        "Observed estimator-variance comparison; includes pilot path cost, not wall time"
    )


def variance_reduction_comparison(
    service: SimulationService,
    request: SimulationRequest,
    target: PathObservable,
    control_observable: PathObservable,
    context: RunContext,
    *,
    known_control_mean: float,
    pilot_key: StreamKey,
    pilot_paths: int,
) -> VarianceReductionComparison:
    if request.sequence.kind != SequenceKind.PSEUDO or request.sequence.antithetic:
        raise SimulationError("Comparison starts from an ordinary pseudo-random design")
    if request.path_count % 2 or request.batch_size % 2:
        raise SimulationError("Comparison requires even evaluation and batch sizes for antithetics")
    if pilot_key == request.sequence.key:
        raise SimulationError("Pilot must use an independent stream address")
    if pilot_key.seed != context.seed:
        raise SimulationError("Comparison pilot must retain the run root seed")
    integer(pilot_paths, "control pilot paths", minimum=2)
    pilot = replace(
        request, path_count=pilot_paths, sequence=replace(request.sequence, key=pilot_key)
    )
    target_values, control_values = [], []
    for batch in service.engine.iter_batches(pilot):
        target_values.append(target(batch))
        control_values.append(control_observable(batch))
    control = fit_control(
        np.concatenate(target_values),
        np.concatenate(control_values),
        known_mean=known_control_mean,
        pilot_key=pilot_key,
        control_name=control_observable.name,
    )
    plain = service.run(request, target, context)
    antithetic = service.run(
        replace(request, sequence=replace(request.sequence, antithetic=True)),
        target,
        context,
    )
    controlled = service.run(
        request, target, context, control=control, control_observable=control_observable
    )
    assert plain.estimate is not None
    base_variance = plain.estimate.standard_error**2
    cases = []
    for name, result, pilot_count in (
        ("plain", plain, 0),
        ("antithetic", antithetic, 0),
        ("control", controlled, pilot_paths),
    ):
        assert result.estimate is not None
        variance = result.estimate.standard_error**2
        gain = (
            None
            if variance == 0
            else require_finite(base_variance / variance, name="variance gain")
        )
        cost = request.path_count + pilot_count
        work_gain = None if gain is None else gain * request.path_count / cost
        cases.append(
            VarianceReductionCase(name, result, pilot_count, request.path_count, gain, work_gain)
        )
    return VarianceReductionComparison(control, tuple(cases))
