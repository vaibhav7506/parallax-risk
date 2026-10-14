"""Injected production/challenger boundaries and bounded actual model evaluations."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.calibration.contracts import CalibrationResult
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.validation.checks import sensitivity
from parallax_risk.domain.validation.contracts import (
    Comparison,
    Metric,
    ModelOutput,
    Tolerance,
    compare,
)
from parallax_risk.domain.validation.uncertainty import (
    UncertaintyBand,
    confidence_level,
    propagate_covariance,
)


class ValidationCase(Protocol):
    @property
    def hash(self) -> str: ...


class ProductionModel[Case: ValidationCase](Protocol):
    def evaluate(self, case: Case) -> ModelOutput: ...


class ChallengerModel[Case: ValidationCase](Protocol):
    def evaluate(self, case: Case) -> ModelOutput: ...


@dataclass(frozen=True, slots=True)
class ValidationLab[Case: ValidationCase]:
    production: ProductionModel[Case]
    challenger: ChallengerModel[Case]

    def compare(self, case: Case, tolerance: Tolerance, reproduction: str) -> Comparison:
        first, second = self.production.evaluate(case), self.challenger.evaluate(case)
        if (
            not isinstance(first, ModelOutput)
            or not isinstance(second, ModelOutput)
            or first.case_hash != case.hash
            or second.case_hash != case.hash
        ):
            raise DomainValidationError("Model adapter returned stale/foreign input evidence")
        return compare(first, second, tolerance, reproduction)


def perturbation_band[Case: ValidationCase](
    model: ProductionModel[Case],
    baseline: Case,
    cases: tuple[Case, ...],
    metric: str,
    *,
    confidence: float = 0.95,
    maximum_evaluations: int = 1000,
) -> UncertaintyBand:
    """Actual parameter ensemble valuations; percentile range, not frequentist CI."""
    if not isinstance(cases, tuple) or len(cases) < 2:
        raise DomainValidationError("Perturbation ensemble requires at least two immutable cases")
    integer(maximum_evaluations, "model evaluation budget")
    confidence = confidence_level(confidence)
    if len(cases) + 1 > maximum_evaluations:
        raise DomainValidationError("Parameter ensemble evaluation budget exceeded")
    original = model.evaluate(baseline)
    results = tuple(model.evaluate(case) for case in cases)
    if (
        not isinstance(original, ModelOutput)
        or any(not isinstance(r, ModelOutput) for r in results)
        or original.case_hash != baseline.hash
        or any(r.case_hash != c.hash for r, c in zip(results, cases, strict=True))
    ):
        raise DomainValidationError("Perturbation model returned stale case evidence")
    selected = original.metric(metric)
    if any(
        r.metric(metric).schema != selected.schema
        or (r.model_name, r.model_version) != (original.model_name, original.model_version)
        for r in results
    ):
        raise DomainValidationError("Parameter ensemble changed model or metric schema")
    draws = tuple(float(r.metric(metric).value) for r in results)
    alpha = (1 - confidence) / 2
    bounds = np.quantile(np.asarray(draws), (alpha, 1 - alpha), method="linear")
    return UncertaintyBand(
        metric,
        selected.unit,
        selected.value,
        float(bounds[0]),
        float(bounds[1]),
        confidence,
        "supplied_parameter_ensemble_percentile_range_not_confidence_interval",
        content_hash((original.hash, tuple(r.hash for r in results), confidence)),
        (
            "Caller-selected perturbation ensemble; no sampling probability law inferred",
            "Actual full model evaluations; does not include every source of uncertainty",
        ),
        draws,
    )


def calibration_band(
    calibration: CalibrationResult,
    revalue: Callable[[tuple[float, ...]], ModelOutput],
    metric: str,
    bumps: tuple[float, ...],
    parameter_units: tuple[str, ...],
    *,
    confidence: float = 0.95,
) -> UncertaintyBand:
    """Revalue fitted parameters locally and propagate available unconstrained covariance."""
    if not isinstance(calibration, CalibrationResult):
        raise DomainValidationError("Calibration propagation requires an actual calibration result")
    calibration.require_converged()
    covariance = calibration.uncertainty.covariance
    if covariance is None or any(calibration.active_bounds):
        raise DomainValidationError("Calibration covariance unavailable or constrained")
    require_tuple(bumps, float, nonempty=True)
    require_tuple(parameter_units, str, nonempty=True)
    fitted = calibration.fitted_parameters
    if len(bumps) != len(fitted) or len(parameter_units) != len(fitted):
        raise DomainValidationError(
            "Parameter bumps and units must align with fitted parameter order"
        )
    original = revalue(fitted)
    if not isinstance(original, ModelOutput):
        raise DomainValidationError("Calibration revaluation requires typed model output")
    selected = original.metric(metric)
    derivatives = []
    for i, (bump, unit) in enumerate(zip(bumps, parameter_units, strict=True)):

        def local(amount: float, index: int = i) -> Metric:
            moved = tuple(
                float(value + amount) if j == index else value for j, value in enumerate(fitted)
            )
            if any(
                not bound.lower <= value <= bound.upper
                for bound, value in zip(calibration.parameter_bounds, moved, strict=True)
            ):
                raise DomainValidationError(
                    "Calibration perturbation exceeds fitted optimizer bounds"
                )
            result = revalue(moved)
            if not isinstance(result, ModelOutput):
                raise DomainValidationError("Calibration revaluation requires typed model output")
            if amount != 0 and (moved == fitted or result.case_hash == original.case_hash):
                raise DomainValidationError("Calibration bump is below input resolution")
            if (result.model_name, result.model_version) != (
                original.model_name,
                original.model_version,
            ):
                raise DomainValidationError("Calibration revaluation changed model identity")
            return result.metric(metric)

        # All h and h/2 moves must be admissible. A failed consistency check is rejected.
        result = sensitivity(
            local,
            bump,
            unit,
            Tolerance(1e-8, 1e-3),
            evidence=(content_hash(calibration),),
            reproduction="Revalue retained calibration and exact parameter bumps",
            version=original.model_version,
        )
        if not result.consistency.passed:
            raise DomainValidationError(
                "Calibration propagation derivatives failed h versus h/2 consistency"
            )
        derivatives.append(result.half_bump_derivative)
    return propagate_covariance(
        selected,
        tuple(derivatives),
        covariance,
        parameter_units,
        content_hash(calibration),
        confidence=confidence,
    )
