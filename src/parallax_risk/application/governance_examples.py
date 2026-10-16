"""Synthetic seven-report workflow, with injected persistence, calibration and search ports."""

import io
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from parallax_risk.application.adversarial_examples import example as adversarial_example
from parallax_risk.application.calibration import CalibrationSolver
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.governance import Governance
from parallax_risk.application.governance_codec import StoredRecord
from parallax_risk.application.governance_reports import Report, ReportKind, make_report
from parallax_risk.application.governed_risk import GovernedXva
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.validation_examples import example as validation_example
from parallax_risk.application.validation_search import SearchOptimizer
from parallax_risk.application.xva import AdditiveXvaCalculator, XvaService
from parallax_risk.application.xva_revaluation import XvaRevaluation
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.governance.contracts import (
    Approval,
    Decision,
    Document,
    Finding,
    Limitation,
    Model,
    ModelStatus,
    Version,
)
from parallax_risk.domain.governance.monitoring import (
    Alert,
    AlertState,
    Evaluation,
    MonitorKind,
    Observation,
    Policy,
    Statistic,
)
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.validation.contracts import Severity


def example(
    governance: Governance, solver: CalibrationSolver, optimizer: SearchOptimizer
) -> tuple[Report, ...]:
    """Fixed synthetic IDs intentionally reject a second write into the same database."""
    now = datetime(2026, 10, 2, tzinfo=UTC)
    later = now + timedelta(hours=1)
    model_id, version_id = "synthetic-phase11-xva", "synthetic-phase11-v1"
    lab = validation_example(solver)
    adversarial = adversarial_example(optimizer)
    inventory = Model(
        model_id,
        "Synthetic additive XVA",
        "research_xva",
        "synthetic-owner",
        "Demonstrate evidence-linked governance",
        ModelStatus.DEVELOPMENT,
        version_id,
        "Existing unilateral/additive XVA research workflow",
        lab.baseline.assumptions,
        "Synthetic USD research only",
        92,
        None,
        date(2027, 1, 2),
    )
    records = []

    def save(record: StoredRecord) -> None:
        # Each concrete call below supplies a supported immutable record.
        records.append(
            governance.record(
                record,
                expected_revision=0,
                actor="synthetic-researcher",
                timestamp=later,
                reason="Synthetic Phase 11 governance demonstration",
            )
        )

    save(inventory)
    save(
        Version(
            version_id,
            model_id,
            lab.baseline.model_version,
            "src/parallax_risk/application/xva_revaluation.py:XvaRevaluation; no commit supplied",
            Document.of(
                {"algorithm": "existing-additive-xva", "paths": lab.xva_inputs.request.path_count}
            ),
            Document.of({"input_experiment_hash": lab.xva_inputs.hash}),
            now,
        )
    )
    save(
        Finding(
            "synthetic-phase11-finding",
            model_id,
            version_id,
            Severity.HIGH,
            "Weak mutation suite retains undetected seeded faults",
            Document.of(
                {
                    "campaign": content_hash(adversarial.weak_suite),
                    "rates": adversarial.weak_suite.rates,
                }
            ),
            "synthetic-validator",
            date(2026, 11, 2),
        )
    )
    save(
        Approval(
            "synthetic-phase11-decision",
            model_id,
            version_id,
            Decision.CONDITIONAL,
            "Synthetic workflow decision; numerical findings remain open",
            Document.of(
                {
                    "validation_output": lab.baseline.hash,
                    "weak_campaign": content_hash(adversarial.weak_suite),
                }
            ),
            ("Research-only use; remediate the retained weak-suite finding",),
            "synthetic-research-committee",
            now,
        )
    )
    save(
        Limitation(
            "synthetic-phase11-limitation",
            model_id,
            version_id,
            "Unilateral/additive research XVA; no default-conditioned MPOR closeout",
            (lab.xva_inputs.book.snapshot_hash,),
            "Synthetic portfolio; no institutional materiality assessment",
            ("Restricted research use; retain all original numerical assumptions",),
        )
    )
    changed = lab.stresses[0].stressed
    baseline = lab.stresses[0].baseline
    metric = baseline.metric("CVA")
    scope = content_hash((lab.xva_inputs.book.snapshot_hash, "CVA", metric.unit))
    policy = Policy(
        "synthetic-phase11-policy",
        model_id,
        version_id,
        MonitorKind.CVA,
        "CVA",
        metric.unit,
        Statistic.ABSOLUTE_CHANGE,
        0.0,
        Severity.MEDIUM,
        "Synthetic zero threshold exposes any actual CVA movement",
    )
    save(policy)
    evaluation = Evaluation(
        "synthetic-phase11-monitor",
        policy,
        Observation("CVA", metric.unit, metric.value, scope, baseline.hash, now),
        Observation("CVA", metric.unit, changed.metric("CVA").value, scope, changed.hash, later),
    )
    save(evaluation)
    if evaluation.triggered:
        save(
            Alert(
                "synthetic-phase11-alert",
                model_id,
                version_id,
                evaluation.evaluation_id,
                policy.severity,
                AlertState.OPEN,
                Document.of(
                    {
                        "evaluation": content_hash(evaluation),
                        "statistic": evaluation.statistic,
                        "threshold": policy.threshold,
                    }
                ),
            )
        )
    logger = create_logger(stream=io.StringIO())
    workflow = XvaRevaluation(
        ExposureService(MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger),
        XvaService(AdditiveXvaCalculator(), logger),
    )
    case = replace(
        lab.xva_inputs,
        run=replace(lab.xva_inputs.run, run_id=RiskRunId("synthetic-phase11-run"), timestamp=now),
    )
    governed = GovernedXva(workflow, governance).run(
        case,
        model_id=model_id,
        version_id=version_id,
        actor="synthetic-researcher",
        recorded=later,
        calibration_id=None,
        code_revision=None,
    )
    records.append(governed.lineage)
    sources = (
        (
            ReportKind.TECHNICAL,
            (adversarial.full_suite.baseline, adversarial.full_suite.baseline_checks),
        ),
        (ReportKind.GOVERNANCE, tuple(records)),
        (ReportKind.COMPARISON, lab.comparison),
        (ReportKind.STRESS, lab.stresses),
        (ReportKind.CONVERGENCE, lab.paths),
        (ReportKind.MUTATION, adversarial.weak_suite),
        (ReportKind.LINEAGE, governed.lineage.record),
    )
    return tuple(
        make_report(
            kind,
            source,
            report_id=f"synthetic-phase11-{kind.value}",
            generated=later,
            is_synthetic=True,
            interpretation="Computed synthetic evidence; retain failures and recorded decisions.",
        )
        for kind, source in sources
    )
