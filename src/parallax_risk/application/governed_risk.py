"""Mandatory lineage persistence for governed XVA runs using the real exposure/XVA engines."""

from dataclasses import dataclass
from datetime import datetime

from parallax_risk.application.governance import Governance, Snapshot
from parallax_risk.application.xva import XvaRunResult
from parallax_risk.application.xva_revaluation import XvaExperiment, XvaRevaluation
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain.governance.contracts import Document, Lineage, Version


@dataclass(frozen=True, slots=True)
class GovernedRun:
    result: XvaRunResult
    lineage: Snapshot


@dataclass(frozen=True, slots=True)
class GovernedXva:
    workflow: XvaRevaluation
    governance: Governance

    def run(
        self,
        case: XvaExperiment,
        *,
        model_id: str,
        version_id: str,
        actor: str,
        recorded: datetime,
        calibration_id: str | None,
        code_revision: str | None,
    ) -> GovernedRun:
        """A returned governed result always has a committed, immutable lineage record.

        Legacy research entry points remain explicitly ungoverned. No revision or
        calibration is inferred: absent values stay null with recorded assumptions.
        """
        if not isinstance(case, XvaExperiment):
            raise DomainValidationError("Governed XVA requires validated experiment inputs")
        version = self.governance.repository.get("version", version_id)
        if (
            version is None
            or not isinstance(version.record, Version)
            or version.record.model_id != model_id
        ):
            raise DomainValidationError("Governed run requires a registered model version")
        if self.governance.repository.get("lineage", str(case.run.run_id)) is not None:
            raise DomainValidationError("Risk run ID already has lineage")
        if recorded < case.run.timestamp:
            raise DomainValidationError("Lineage audit cannot precede the run timestamp")
        paths = self.workflow.exposure.run(
            case.request,
            case.book,
            case.markets,
            case.run,
            accounts=case.accounts,
            credit=case.credit,
        )
        result = self.workflow.xva.value(
            paths, case.discount, case.credit, case.own, case.funding, case.margins, case.run
        )
        csas = tuple(
            content_hash(netting.csa)
            for counterparty in case.book.counterparties
            for netting in counterparty.netting_sets
            if netting.csa is not None
        )
        configuration = content_hash(
            (
                case.request,
                case.book,
                case.markets.hash,
                case.accounts,
                tuple(c.hash for c in case.credit),
                case.own,
                case.discount,
                case.funding,
                case.margins,
            )
        )
        assumptions = result.result.assumptions + (
            "Lineage fingerprints retain input identities, not the input bytes; "
            "retain source snapshots for replay.",
            "Calibration ID is caller-supplied and is not a calibration-result repository.",
        )
        if calibration_id is None:
            assumptions += ("No calibration ID supplied; inputs are explicitly parameterized.",)
        if code_revision is None:
            assumptions += ("No source revision supplied; no commit identity inferred.",)
        lineage = Lineage(
            str(case.run.run_id),
            model_id,
            version_id,
            code_revision,
            paths.portfolio_hash,
            paths.market_scenario_hash,
            configuration,
            calibration_id,
            case.request.sequence.key.seed,
            Document.of(
                {
                    "market": case.request.sequence,
                    "credit": tuple(
                        (str(c.counterparty_id), c.kind, c.threshold_key, c.rank_key)
                        for c in case.credit
                    ),
                }
            ),
            csas,
            case.run.timestamp,
            Document.of(
                {
                    "simulation": paths.simulation,
                    "run_context": case.run,
                    "market_path_digest": paths.market_path_digest,
                    "initial_account_hashes": paths.initial_account_hashes,
                    "model_version_hash": encode_version(version.record),
                }
            ),
            content_hash((result.exposure_hash, result.result.hash)),
            assumptions,
        )
        snapshot = self.governance.record(
            lineage,
            expected_revision=0,
            actor=actor,
            timestamp=recorded,
            reason="Completed governed XVA run; immutable input/result lineage",
        )
        return GovernedRun(result, snapshot)


def encode_version(version: Version) -> str:
    return content_hash(version)
