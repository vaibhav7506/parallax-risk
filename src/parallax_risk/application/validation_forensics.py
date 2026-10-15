"""Actual repeat and counterfactual evaluations for material-change diagnostics."""

from dataclasses import dataclass

from parallax_risk.application.validation import ProductionModel, ValidationCase
from parallax_risk.application.xva_revaluation import XvaExperiment
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain._validation import require_text, require_token
from parallax_risk.domain.pricing._numbers import total
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.validation.checks import equality
from parallax_risk.domain.validation.contracts import Check, ModelOutput, Tolerance, check
from parallax_risk.domain.validation.forensics import (
    CauseKind,
    DiagnosticCause,
    DiagnosticContext,
    DiagnosticStep,
    ForensicReport,
)
from parallax_risk.domain.xva.contracts import fingerprint


@dataclass(frozen=True, slots=True)
class DiagnosticState[Case: ValidationCase]:
    case: Case
    context: DiagnosticContext

    def __post_init__(self) -> None:
        if not isinstance(self.context, DiagnosticContext):
            raise DomainValidationError("Diagnostics require explicit input context")
        fingerprint(self.case.hash)


@dataclass(frozen=True, slots=True)
class Counterfactual[Case: ValidationCase]:
    name: str
    possible_cause: CauseKind
    state: DiagnosticState[Case]

    def __post_init__(self) -> None:
        require_token(self.name)
        if not isinstance(self.possible_cause, CauseKind) or not isinstance(
            self.state, DiagnosticState
        ):
            raise DomainValidationError(
                "Counterfactual needs a typed possible cause and actual state"
            )


def xva_context(case: XvaExperiment, calibration_hash: str) -> DiagnosticContext:
    """Actual inputs; supplied calibration hash or explicitly hashed absence."""
    fingerprint(calibration_hash)
    if not isinstance(case, XvaExperiment):
        raise DomainValidationError("XVA diagnostic context requires the complete experiment")
    return DiagnosticContext(
        content_hash(
            (
                case.discount,
                case.markets.hash,
                tuple(c.initial_state for c in case.request.components),
            )
        ),
        case.book.snapshot_hash,
        calibration_hash,
        content_hash(
            (
                tuple(c.process for c in case.request.components),
                case.request.correlation,
                tuple(c.hash for c in case.credit),
                case.own,
                case.funding,
                case.margins,
            )
        ),
        content_hash(
            (
                case.request.grid,
                case.request.path_count,
                case.request.batch_size,
                case.request.sequence,
                tuple(c.scheme for c in case.request.components),
            )
        ),
        content_hash(
            (
                case.accounts,
                tuple(
                    (str(n.netting_set_id), n.csa)
                    for c in case.book.counterparties
                    for n in c.netting_sets
                ),
            )
        ),
    )


def diagnose[Case: ValidationCase](
    model: ProductionModel[Case],
    before: DiagnosticState[Case],
    after: DiagnosticState[Case],
    counterfactuals: tuple[Counterfactual[Case], ...],
    metric: str,
    materiality: Tolerance,
    repeatability: Tolerance,
    reproduction: str,
    *,
    maximum_evaluations: int = 100,
) -> ForensicReport:
    require_text(reproduction)
    require_token(metric)
    integer(maximum_evaluations, "diagnostic evaluation budget")
    if (
        not isinstance(before, DiagnosticState)
        or not isinstance(after, DiagnosticState)
        or not isinstance(materiality, Tolerance)
        or not isinstance(repeatability, Tolerance)
        or not isinstance(counterfactuals, tuple)
        or any(not isinstance(c, Counterfactual) for c in counterfactuals)
        or len({c.name for c in counterfactuals}) != len(counterfactuals)
        or len(counterfactuals) + 4 > maximum_evaluations
    ):
        raise DomainValidationError("Diagnostic states, unique steps, tolerances or budget invalid")

    def evaluate(state: DiagnosticState[Case]) -> ModelOutput:
        output = model.evaluate(state.case)
        if not isinstance(output, ModelOutput) or output.case_hash != state.case.hash:
            raise DomainValidationError("Diagnostic model returned stale input evidence")
        return output

    first, last = evaluate(before), evaluate(after)
    a, b = first.metric(metric), last.metric(metric)
    if a.schema != b.schema:
        raise DomainValidationError("Diagnostic endpoints require matching metric/unit schemas")
    change = total((b.value, -a.value))
    significant = check(
        "material-change",
        b,
        abs(change),
        materiality.bound(a.value),
        evidence=(first.hash, last.hash, "Failure means material change, not model invalidity"),
        reproduction=reproduction,
        version=last.model_version,
    )
    repeat_first, repeat_last = evaluate(before), evaluate(after)
    repeat_checks: list[Check] = []
    for original, repeated in ((first, repeat_first), (last, repeat_last)):
        if repeated.metric(metric).schema != original.metric(metric).schema or (
            repeated.model_name,
            repeated.model_version,
        ) != (original.model_name, original.model_version):
            raise DomainValidationError("Repeat changed model identity or metric schema")
        repeat_checks.append(
            equality(
                f"repeat-{len(repeat_checks)}",
                repeated.metric(metric),
                original.metric(metric).value,
                repeatability,
                evidence=(original.hash, repeated.hash),
                reproduction=reproduction,
                version=repeated.model_version,
            )
        )
    kinds_fields = (
        (CauseKind.MARKET, "market"),
        (CauseKind.PORTFOLIO, "portfolio"),
        (CauseKind.CALIBRATION, "calibration"),
        (CauseKind.PARAMETERS, "parameters"),
        (CauseKind.NUMERICS, "numerics"),
        (CauseKind.COLLATERAL, "collateral"),
    )
    causes = [
        DiagnosticCause(
            k,
            getattr(before.context, field) != getattr(after.context, field),
            getattr(before.context, field),
            getattr(after.context, field),
            "Input fingerprint changed; numerics changes need separate convergence evidence",
        )
        for k, field in kinds_fields
    ]
    causes.append(
        DiagnosticCause(
            CauseKind.VERSION,
            (first.model_name, first.model_version) != (last.model_name, last.model_version),
            f"{first.model_name}:{first.model_version}",
            f"{last.model_name}:{last.model_version}",
            "Observed adapter identity; not a causal valuation attribution",
        )
    )
    # An unchanged numerical configuration can still produce failed actual reruns.
    if not all(c.passed for c in repeat_checks):
        causes = [
            DiagnosticCause(
                c.kind,
                True,
                c.before,
                c.after,
                "Actual same-input repeated valuations exceeded declared repeatability tolerance",
            )
            if c.kind == CauseKind.NUMERICS
            else c
            for c in causes
        ]
    previous = first
    steps = []
    for item in counterfactuals:
        output = evaluate(item.state)
        current = output.metric(metric)
        if current.schema != a.schema:
            raise DomainValidationError("Counterfactual changed metric/unit schema")
        steps.append(
            DiagnosticStep(
                item.name,
                item.possible_cause,
                output,
                item.state.context,
                total((current.value, -previous.metric(metric).value)),
            )
        )
        previous = output
    residual = total((change, -total(tuple(s.change for s in steps))))
    return ForensicReport(
        metric,
        a.unit,
        first,
        last,
        before.context,
        after.context,
        change,
        significant,
        tuple(causes),
        tuple(steps),
        residual,
        (repeat_first, repeat_last),
        (repeat_checks[0], repeat_checks[1]),
        reproduction,
    )
