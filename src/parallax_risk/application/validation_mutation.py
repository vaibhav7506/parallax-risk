"""Injected isolated mutants; no monkeypatch, production switch or swallowed errors."""

from collections.abc import Callable
from typing import Protocol

from parallax_risk.application.validation import ValidationCase
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.validation.contracts import Check, ModelOutput
from parallax_risk.domain.validation.mutation import (
    DetectionRate,
    Mutation,
    MutationCampaign,
    MutationEvidence,
)


class MutationModel[Case: ValidationCase](Protocol):
    def evaluate(self, case: Case, mutation: Mutation | None) -> ModelOutput: ...


def campaign[Case: ValidationCase](
    model: MutationModel[Case],
    case: Case,
    mutations: tuple[Mutation, ...],
    suite: Callable[[ModelOutput], tuple[Check, ...]],
    reproduction: str,
    *,
    maximum_evaluations: int = 100,
) -> MutationCampaign:
    require_tuple(mutations, Mutation, nonempty=True)
    require_text(reproduction)
    integer(maximum_evaluations, "mutation evaluation budget")
    if (
        len(mutations) + 1 > maximum_evaluations
        or len({m.name for m in mutations}) != len(mutations)
        or "ALL" in {m.category for m in mutations}
    ):
        raise DomainValidationError("Mutation budget exceeded or duplicate identifiers")

    def execute(mutation: Mutation | None) -> tuple[ModelOutput, tuple[Check, ...]]:
        output = model.evaluate(case, mutation)
        if not isinstance(output, ModelOutput) or output.case_hash != case.hash:
            raise DomainValidationError("Mutation model returned stale input evidence")
        checks = suite(output)
        require_tuple(checks, Check, nonempty=True)
        if len({c.name for c in checks}) != len(checks) or any(
            type(c.passed) is not bool for c in checks
        ):
            raise DomainValidationError("Mutation checks require unique names and boolean results")
        for result in checks:
            require_token(result.name)
            output.metric(result.metric)
            require_tuple(result.evidence, str, nonempty=True)
            for item in result.evidence:
                require_text(item)
            if (
                require_finite(result.observed, name="mutation discrepancy") < 0
                or require_finite(result.allowed, name="mutation tolerance") < 0
                or result.passed != (result.observed <= result.allowed)
                or (result.finding is None) != result.passed
            ):
                raise DomainValidationError(
                    "Mutation check result is inconsistent with its evidence"
                )
        return output, checks

    baseline, baseline_checks = execute(None)
    evidence = []
    for mutation in mutations:
        output, checks = execute(mutation)
        if tuple((c.name, c.metric, c.allowed) for c in checks) != tuple(
            (c.name, c.metric, c.allowed) for c in baseline_checks
        ) or tuple(m.schema for m in output.metrics) != tuple(m.schema for m in baseline.metrics):
            raise DomainValidationError("Mutant changed validation or metric schemas")
        failed = tuple(
            c.name
            for b, c in zip(baseline_checks, checks, strict=True)
            if b.passed and not c.passed
        )
        evidence.append(MutationEvidence(mutation, output, checks, failed, bool(failed)))
    categories = ("ALL", *sorted({m.category for m in mutations}))
    rates = []
    for category in categories:
        group = [e for e in evidence if category == "ALL" or e.mutation.category == category]
        detected = sum(e.detected for e in group)
        rates.append(DetectionRate(category, detected, len(group), detected / len(group)))
    return MutationCampaign(baseline, baseline_checks, tuple(evidence), tuple(rates), reproduction)
