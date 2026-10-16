"""Evidence-only report construction and deterministic escaped HTML/JSON rendering."""

import html
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from parallax_risk.application.governance import Snapshot
from parallax_risk.application.validation_stress import StressResult
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.governance.contracts import Document, Lineage
from parallax_risk.domain.validation.checks import ConvergenceStudy
from parallax_risk.domain.validation.contracts import Check, Comparison, ModelOutput
from parallax_risk.domain.validation.mutation import MutationCampaign


class ReportKind(StrEnum):
    TECHNICAL = "technical_validation"
    GOVERNANCE = "governance_summary"
    COMPARISON = "model_comparison"
    STRESS = "stress"
    CONVERGENCE = "convergence"
    MUTATION = "mutation_test"
    LINEAGE = "risk_run_lineage"


@dataclass(frozen=True, slots=True)
class Report:
    report_id: str
    kind: ReportKind
    title: str
    generated: datetime
    is_synthetic: bool
    evidence: Document
    interpretation: str

    def __post_init__(self) -> None:
        require_token(self.report_id)
        require_text(self.title)
        require_text(self.interpretation)
        if (
            not isinstance(self.kind, ReportKind)
            or type(self.is_synthetic) is not bool
            or not isinstance(self.evidence, Document)
        ):
            raise DomainValidationError("Typed report metadata and evidence are required")
        object.__setattr__(self, "generated", utc_timestamp(self.generated))

    @property
    def document(self) -> Document:
        return Document.of(
            {
                "schema": 1,
                "project": "Parallax Risk",
                "report": self,
                "evidence_hash": self.evidence.hash,
                "governance_notice": (
                    "Recorded decisions are research workflow metadata; "
                    "no regulatory approval or authenticated signature is implied."
                ),
            }
        )

    def json(self) -> str:
        return (
            json.dumps(
                self.document.value(), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
            )
            + "\n"
        )

    def html(self) -> str:
        """No scripts, remote assets, active links or unescaped stored evidence."""
        escaped = html.escape(self.json(), quote=True)
        title = html.escape(self.title, quote=True)
        interpretation = html.escape(self.interpretation, quote=True)
        return (
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" '
            "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>{title}</title><style>"
            "body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:1rem}"
            f"</style></head><body><h1>Parallax Risk — {title}</h1>"
            f"<p>{interpretation}</p><p>Synthetic evidence: {str(self.is_synthetic).lower()}. "
            f"Evidence SHA-256: {self.evidence.hash}</p><pre>{escaped}</pre></body></html>\n"
        )


def make_report(
    kind: ReportKind,
    evidence: object,
    *,
    report_id: str,
    generated: datetime,
    is_synthetic: bool,
    interpretation: str,
) -> Report:
    """Only declared computed result types can enter the seven report workflows.

    Narrative is explicitly caller-authored; the renderer infers no model conclusion.
    Original assumptions, failed checks, residuals and mutation misses remain intact.
    """
    if not isinstance(kind, ReportKind):
        raise DomainValidationError("An explicit report kind is required")
    match kind:
        case ReportKind.TECHNICAL:
            if (
                not isinstance(evidence, tuple)
                or len(evidence) != 2
                or not isinstance(evidence[0], ModelOutput)
            ):
                raise DomainValidationError("Technical reports require model output and checks")
            require_tuple(evidence[1], Check, nonempty=True)
        case ReportKind.GOVERNANCE:
            require_tuple(evidence, Snapshot, nonempty=True)  # type: ignore[arg-type]
        case ReportKind.COMPARISON:
            if not isinstance(evidence, Comparison):
                raise DomainValidationError("Comparison report requires a computed comparison")
        case ReportKind.STRESS:
            require_tuple(evidence, StressResult, nonempty=True)  # type: ignore[arg-type]
        case ReportKind.CONVERGENCE:
            if not isinstance(evidence, ConvergenceStudy):
                raise DomainValidationError("Convergence report requires a computed study")
        case ReportKind.MUTATION:
            if not isinstance(evidence, MutationCampaign):
                raise DomainValidationError("Mutation report requires an executed campaign")
        case ReportKind.LINEAGE:
            if not isinstance(evidence, Lineage):
                raise DomainValidationError("Lineage report requires a validated run record")
    return Report(
        report_id,
        kind,
        kind.value.replace("_", " "),
        generated,
        is_synthetic,
        Document.of({"result": evidence}),
        interpretation,
    )
