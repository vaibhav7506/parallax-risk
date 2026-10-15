"""Injected bounded objective and actual paired valuations with every input retained."""

import math
from collections.abc import Callable
from typing import Protocol

from parallax_risk.application.validation import ChallengerModel, ProductionModel, ValidationCase
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.validation.contracts import ModelOutput
from parallax_risk.domain.validation.search import (
    OptimizerResult,
    SearchEvaluation,
    SearchResult,
    SearchSpec,
)


class SearchOptimizer(Protocol):
    def maximize(
        self, objective: Callable[[tuple[float, ...]], float], spec: SearchSpec
    ) -> OptimizerResult: ...


def feasible(parameters: tuple[float, ...], spec: SearchSpec) -> bool:
    if not isinstance(parameters, tuple) or len(parameters) != len(spec.dimensions):
        raise DomainValidationError("Search parameters must match ordered dimensions")
    for value in parameters:
        require_finite(value, name="search parameter")
    return all(
        d.lower <= v <= d.upper for d, v in zip(spec.dimensions, parameters, strict=True)
    ) and all(
        c.lower <= math.fsum(w * v for w, v in zip(c.weights, parameters, strict=True)) <= c.upper
        for c in spec.restrictions
    )


def search[Case: ValidationCase](
    production: ProductionModel[Case],
    challenger: ChallengerModel[Case],
    build_case: Callable[[tuple[float, ...]], Case],
    optimizer: SearchOptimizer,
    spec: SearchSpec,
) -> SearchResult:
    if not isinstance(spec, SearchSpec):
        raise DomainValidationError("Search requires explicit validated specification")
    evaluations: list[SearchEvaluation] = []
    identity: tuple[str, str, str, str] | None = None
    schema: tuple[str, str, tuple[str, ...]] | None = None

    def objective(parameters: tuple[float, ...]) -> float:
        nonlocal identity, schema
        if not feasible(parameters, spec):
            raise DomainValidationError("Optimizer requested infeasible inputs; no clipping")
        if len(evaluations) >= spec.maximum_evaluations:
            raise DomainValidationError("Actual paired valuation budget exhausted")
        case = build_case(parameters)
        first, second = production.evaluate(case), challenger.evaluate(case)
        if (
            not isinstance(first, ModelOutput)
            or not isinstance(second, ModelOutput)
            or first.case_hash != case.hash
            or second.case_hash != case.hash
        ):
            raise DomainValidationError("Search adapter returned stale case evidence")
        p, c = first.metric(spec.metric), second.metric(spec.metric)
        current = (first.model_name, first.model_version, second.model_name, second.model_version)
        if (
            p.schema != c.schema
            or (schema is not None and schema != p.schema)
            or (identity is not None and identity != current)
        ):
            raise DomainValidationError("Search changed model identity or metric/unit schema")
        identity, schema = current, p.schema
        discrepancy = require_finite(abs(p.value - c.value), name="absolute model discrepancy")
        evaluations.append(SearchEvaluation(parameters, first, second, discrepancy))
        return discrepancy

    result = optimizer.maximize(objective, spec)
    if not isinstance(result, OptimizerResult) or not evaluations:
        raise DomainValidationError("Optimizer returned no actual feasible evaluation")
    integer(result.evaluations, "reported paired evaluations")
    integer(result.iterations, "reported optimizer iterations", minimum=0)
    require_text(result.message)
    require_text(result.implementation)
    best = max(evaluations, key=lambda e: e.discrepancy)
    if (
        type(result.converged) is not bool
        or not feasible(result.parameters, spec)
        or result.parameters != best.parameters
        or result.objective != best.discrepancy
        or result.evaluations != len(evaluations)
        or result.iterations > spec.maximum_iterations
    ):
        raise DomainValidationError(
            "Optimizer result inconsistent with retained feasible evaluations"
        )
    return SearchResult(spec, result, best, tuple(evaluations))
