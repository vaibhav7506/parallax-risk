"""Authenticated service workflows; persistence and numerical engines are injected."""

import json
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from parallax_risk import __version__
from parallax_risk.application.access import Principal, Role, ServiceError
from parallax_risk.application.calibration import CalibrationRunResult
from parallax_risk.application.governance import Governance, Snapshot
from parallax_risk.application.governance_codec import decode as decode_governance
from parallax_risk.application.governance_reports import ReportKind, make_report
from parallax_risk.application.jobs import (
    Job,
    JobBrief,
    JobRepository,
    JobStatus,
    ObjectBrief,
    ObjectRepository,
    StoredObject,
)
from parallax_risk.application.validation_stress import StressResult
from parallax_risk.application.wire import decode, document
from parallax_risk.application.workflows import Command, Operation, Workflows, walk
from parallax_risk.common.canonical import JsonValue, content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import Identifier
from parallax_risk.domain.calibration.problems import VasicekBondProblem
from parallax_risk.domain.exposure.contracts import CreditScenario
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario
from parallax_risk.domain.governance.contracts import (
    Approval,
    Document,
    Lineage,
    Model,
    ModelStatus,
    Version,
)
from parallax_risk.domain.market.snapshot import MarketSnapshot
from parallax_risk.domain.models.rates import Vasicek
from parallax_risk.domain.portfolio.contracts import Counterparty, NettingSet, PortfolioSnapshot
from parallax_risk.domain.portfolio.csa import Csa
from parallax_risk.domain.pricing.engine import PricingContext
from parallax_risk.domain.simulation.contracts import SimulationRequest
from parallax_risk.domain.validation.checks import ConvergenceStudy
from parallax_risk.domain.validation.contracts import Comparison
from parallax_risk.domain.validation.mutation import MutationCampaign

OBJECT_TYPES: dict[str, type[object]] = {
    "market": MarketSnapshot,
    "portfolio": PortfolioSnapshot,
    "counterparty": Counterparty,
    "netting": NettingSet,
    "csa": Csa,
    "scenario": ConditionalMarketScenario,
    "pricing-context": PricingContext,
}
GOVERNANCE_KINDS = frozenset(
    (
        "model",
        "version",
        "finding",
        "approval",
        "limitation",
        "lineage",
        "policy",
        "evaluation",
        "alert",
    )
)


def page(after: str, limit: int) -> None:
    if after:
        Identifier(after)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise DomainValidationError("Page size must be 1–100")


def _natural_key(item: object) -> str | None:
    if isinstance(item, PortfolioSnapshot):
        return str(item.portfolio_id) + ":" + str(item.version)
    if isinstance(item, MarketSnapshot):
        return str(item.snapshot_id) + ":" + str(item.version)
    if isinstance(item, ConditionalMarketScenario):
        return item.hash
    return None


@dataclass(frozen=True, slots=True)
class RiskService:
    workflows: Workflows
    jobs: JobRepository
    objects: ObjectRepository
    governance: Governance
    maximum_pending: int = 64

    def ingest(
        self, principal: Principal, kind: str, key: str, payload: JsonValue, now: datetime
    ) -> StoredObject:
        principal.require(Role.ANALYST)
        if kind not in OBJECT_TYPES:
            raise ServiceError(404, "object_kind_unknown")
        Identifier(key)
        item = decode(payload, OBJECT_TYPES[kind])
        natural = _natural_key(item)
        if natural is not None and key != natural:
            raise DomainValidationError("Object key must equal its declared immutable identity")
        return self.objects.put(StoredObject(principal.subject, kind, key, document(item), now))

    def get_object(self, principal: Principal, kind: str, key: str) -> StoredObject:
        principal.require(Role.READER)
        Identifier(key)
        item = self.objects.get(principal.subject, kind, key)
        if item is None:
            raise ServiceError(404, "object_not_found")
        return item

    def object_page(
        self, principal: Principal, kind: str, after: str, limit: int
    ) -> tuple[ObjectBrief, ...]:
        principal.require(Role.READER)
        if kind not in OBJECT_TYPES and kind != "report":
            raise ServiceError(404, "object_kind_unknown")
        page(after, limit)
        return self.objects.list(principal.subject, kind, after, limit)

    def portfolio_parts(self, principal: Principal, key: str, kind: str) -> object:
        book = decode(
            self.get_object(principal, "portfolio", key).document.value()["value"],
            PortfolioSnapshot,
        )
        if kind == "counterparties":
            return book.counterparties
        sets = tuple(n for c in book.counterparties for n in c.netting_sets)
        if kind == "netting-sets":
            return sets
        if kind == "csas":
            return tuple(n.csa for n in sets if n.csa is not None)
        raise ServiceError(404, "portfolio_projection_unknown")

    def _version(self, model_id: str, version_id: str) -> Snapshot:
        Identifier(model_id)
        Identifier(version_id)
        snapshot = self.governance.repository.get("version", version_id)
        if (
            snapshot is None
            or not isinstance(snapshot.record, Version)
            or snapshot.record.model_id != model_id
        ):
            raise DomainValidationError("Registered matching model/version required")
        return snapshot

    def _retained_inputs(self, owner: str, command: Command) -> None:
        for item in walk(command):
            kind = (
                "portfolio"
                if isinstance(item, PortfolioSnapshot)
                else "market"
                if isinstance(item, MarketSnapshot)
                else "scenario"
                if isinstance(item, ConditionalMarketScenario)
                else None
            )
            if kind is not None:
                natural = _natural_key(item)
                assert natural is not None
                saved = self.objects.get(owner, kind, natural)
                if saved is None or saved.document.hash != document(item).hash:
                    raise DomainValidationError(
                        "Register the exact portfolio/market/scenario input before submitting"
                    )

    def submit(
        self,
        principal: Principal,
        operation: Operation,
        payload: JsonValue,
        *,
        model_id: str,
        version_id: str,
        is_synthetic: bool,
        idempotency_key: str,
        correlation_id: str,
        now: datetime,
        calibration_job: str | None = None,
    ) -> Job:
        principal.require(Role.ANALYST)
        Identifier(idempotency_key)
        Identifier(correlation_id)
        if type(is_synthetic) is not bool:
            raise DomainValidationError("Synthetic status must be declared")
        self._version(model_id, version_id)
        command = self.workflows.prepare(operation, payload)
        self._retained_inputs(principal.subject, command)
        if calibration_job is not None:
            source = self.job(principal, calibration_job)
            if (
                source.operation != Operation.CALIBRATION
                or source.status != JobStatus.SUCCEEDED
                or source.result is None
            ):
                raise DomainValidationError(
                    "Calibration reference requires a successful owned calibration job"
                )
            calibrated = decode(source.result.value()["value"], CalibrationRunResult).calibration
            calibrated.require_converged()
            original = self.workflows.prepare(source.operation, source.request.value()["payload"])
            from parallax_risk.application.workflows import CalibrationCommand

            if isinstance(original, CalibrationCommand) and isinstance(
                original.problem, VasicekBondProblem
            ):
                processes = tuple(n for n in walk(command) if isinstance(n, Vasicek))
                if not processes or not any(
                    tuple(getattr(p, b.name) for b in calibrated.parameter_bounds)
                    == calibrated.fitted_parameters
                    for p in processes
                ):
                    raise DomainValidationError(
                        "Referenced Vasicek calibration parameters must appear "
                        "in the submitted processes"
                    )
            else:
                raise DomainValidationError(
                    "Linked deployment currently supports Vasicek bond calibration"
                )
        from parallax_risk.domain.market.observations import SourceMetadata

        if not is_synthetic and any(
            isinstance(n, SourceMetadata) and n.is_sample for n in walk(command)
        ):
            raise DomainValidationError("Synthetic market data cannot be relabelled as observed")
        request = Document(
            json.dumps(
                {
                    "payload": payload,
                    "is_synthetic": is_synthetic,
                    "calibration_job": calibration_job,
                },
                allow_nan=False,
            )
        )
        job = Job(
            uuid4().hex,
            principal.subject,
            operation,
            request,
            model_id,
            version_id,
            correlation_id,
            JobStatus.QUEUED,
            now,
            now,
            None,
            None,
            None,
        )
        return self.jobs.submit(job, idempotency_key, self.maximum_pending)

    def job(self, principal: Principal, job_id: str) -> Job:
        principal.require(Role.READER)
        Identifier(job_id)
        item = self.jobs.get(principal.subject, job_id)
        if item is None:
            raise ServiceError(404, "job_not_found")
        return item

    def job_page(self, principal: Principal, after: str, limit: int) -> tuple[JobBrief, ...]:
        principal.require(Role.READER)
        page(after, limit)
        return self.jobs.list(principal.subject, after, limit)

    def abandon(self, principal: Principal, job_id: str, now: datetime) -> None:
        principal.require(Role.OPERATOR)
        self.job(principal, job_id)
        self.jobs.abandon(principal.subject, job_id, now)

    def governance_get(self, principal: Principal, kind: str, key: str) -> Snapshot:
        principal.require(Role.READER)
        if kind not in GOVERNANCE_KINDS:
            raise ServiceError(404, "governance_kind_unknown")
        Identifier(key)
        snapshot = self.governance.repository.get(kind, key)
        if snapshot is None:
            raise ServiceError(404, "governance_record_not_found")
        return snapshot

    def governance_write(
        self,
        principal: Principal,
        payload: dict[str, JsonValue],
        expected_revision: int,
        reason: str,
        now: datetime,
    ) -> Snapshot:
        record = decode_governance(Document(json.dumps(payload, allow_nan=False)))
        role = (
            Role.APPROVER
            if isinstance(record, Approval)
            or isinstance(record, Model)
            and record.status == ModelStatus.ACTIVE
            else Role.VALIDATOR
        )
        principal.require(role)
        if isinstance(record, Approval) and record.authority != principal.subject:
            raise ServiceError(403, "approval_authority_must_match_authenticated_subject")
        if isinstance(record, Lineage):
            raise ServiceError(403, "service_lineage_is_computed")
        return self.governance.record(
            record,
            expected_revision=expected_revision,
            actor=principal.subject,
            timestamp=now,
            reason=reason,
        )

    def governance_page(
        self, principal: Principal, kind: str, after: str, limit: int
    ) -> tuple[Snapshot, ...]:
        principal.require(Role.READER)
        if kind not in GOVERNANCE_KINDS:
            raise ServiceError(404, "governance_kind_unknown")
        page(after, limit)
        return self.governance.repository.list(kind, after, limit)

    def compute(self, job: Job, now: datetime) -> Document:
        """Internal worker boundary: actual computation, lineage commit, then completion."""
        version = self._version(job.model_id, job.version_id)
        command = self.workflows.prepare(job.operation, job.request.value()["payload"])
        result = document(self.workflows.execute(command))
        if len(result.text.encode("utf-8")) > self.workflows.limits.maximum_output_bytes:
            raise DomainValidationError("Computed output exceeds service result budget")
        nodes = walk(command)
        books = tuple(
            {b.snapshot_hash: b for b in nodes if isinstance(b, PortfolioSnapshot)}.values()
        )
        market_hashes = tuple(
            sorted(
                {
                    m.snapshot_hash if isinstance(m, MarketSnapshot) else m.hash
                    for m in nodes
                    if isinstance(m, (MarketSnapshot, ConditionalMarketScenario))
                }
            )
        )
        requests = tuple({r.hash: r for r in nodes if isinstance(r, SimulationRequest)}.values())
        seeds = {r.sequence.key.seed for r in requests}
        absent_book = content_hash("Declared non-portfolio workflow; no portfolio supplied")
        absent_market = content_hash(
            "Declared analytical/parameter workflow; no market snapshot supplied"
        )
        book_hashes = tuple(sorted(b.snapshot_hash for b in books))
        portfolio_hash = (
            absent_book
            if not book_hashes
            else book_hashes[0]
            if len(book_hashes) == 1
            else content_hash(book_hashes)
        )
        market_hash = (
            absent_market
            if not market_hashes
            else market_hashes[0]
            if len(market_hashes) == 1
            else content_hash(market_hashes)
        )
        sequence = Document.of(
            {
                "market": tuple(r.sequence for r in requests),
                "credit": tuple(
                    (str(c.counterparty_id), c.kind, c.threshold_key, c.rank_key)
                    for c in nodes
                    if isinstance(c, CreditScenario)
                ),
            }
        )
        csas = tuple(
            sorted(
                {
                    content_hash(n.csa)
                    for b in books
                    for c in b.counterparties
                    for n in c.netting_sets
                    if n.csa is not None
                }
            )
        )
        environment = Document.of(
            {
                "release": __version__,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "request_hashes": tuple(r.hash for r in requests),
                "portfolio_hashes": book_hashes,
                "market_hashes": market_hashes,
                "model_version_hash": document(version.record).hash,
                "job_operation": job.operation.value,
                "correlation_id": job.correlation_id,
            }
        )
        calibration_reference = job.request.value()["calibration_job"]
        if calibration_reference is not None and not isinstance(calibration_reference, str):
            raise DomainValidationError("Invalid retained calibration reference")
        lineage = Lineage(
            job.job_id,
            job.model_id,
            job.version_id,
            None,
            portfolio_hash,
            market_hash,
            job.request.hash,
            calibration_reference,
            next(iter(seeds)) if len(seeds) == 1 else None,
            sequence,
            csas,
            job.created,
            environment,
            result.hash,
            (
                (
                    "Actual schema-1 request and result are retained in the durable job; "
                    "input registrations are immutable."
                ),
                (
                    "No authenticated source commit inferred. Calibration is a retained "
                    "successful owned-job reference when supplied; otherwise null."
                ),
                (
                    "Absent portfolio/market use explicit absence fingerprints; multiple "
                    "inputs use listed aggregate hashes."
                ),
                (
                    "Synthetic status is declared and sample-source flags cannot be "
                    "downgraded; actor authenticated by the configured adapter."
                ),
                (
                    "Numerical models retain their earlier versions and research "
                    "limitations; service authorization is not institutional model "
                    "approval."
                ),
            ),
        )
        self.governance.record(
            lineage,
            expected_revision=0,
            actor=job.owner,
            timestamp=max(now, datetime.now(UTC)),
            reason="Completed service computation; retained request/result and immutable lineage",
        )
        return result

    def create_report(
        self,
        principal: Principal,
        kind: ReportKind,
        key: str,
        source_job: str | None,
        governance_keys: tuple[tuple[str, str], ...],
        interpretation: str,
        now: datetime,
        governance_synthetic: bool | None = None,
    ) -> StoredObject:
        principal.require(Role.ANALYST)
        Identifier(key)
        synthetic = False
        if kind == ReportKind.GOVERNANCE:
            if type(governance_synthetic) is not bool:
                raise DomainValidationError("Declare synthetic status for governance evidence")
            synthetic = governance_synthetic
            if source_job is not None or not governance_keys or len(governance_keys) > 100:
                raise DomainValidationError(
                    "Governance report needs 1–100 stored record references"
                )
            evidence: object = tuple(
                self.governance_get(principal, k, i) for k, i in governance_keys
            )
        else:
            if governance_synthetic is not None:
                raise DomainValidationError("Computed report synthetic status comes from its job")
            if source_job is None or governance_keys:
                raise DomainValidationError(
                    "Computed report needs exactly one successful job reference"
                )
            job = self.job(principal, source_job)
            if job.status != JobStatus.SUCCEEDED or job.result is None:
                raise DomainValidationError("Report requires a successful retained job")
            synthetic = job.request.value()["is_synthetic"] is True
            stored = job.result.value()["value"]
            if kind == ReportKind.LINEAGE:
                evidence = self.governance_get(principal, "lineage", job.job_id).record
            elif (
                kind in (ReportKind.COMPARISON, ReportKind.TECHNICAL)
                and job.operation == Operation.COMPARISON
            ):
                comparison = decode(stored, Comparison)
                evidence = (
                    comparison
                    if kind == ReportKind.COMPARISON
                    else (comparison.production, tuple(d.check for d in comparison.differences))
                )
            elif kind == ReportKind.STRESS and job.operation == Operation.STRESS:
                # Fixed expected tuple root, selected by the server, never a client type name.
                from parallax_risk.application.wire import _decode

                evidence = _decode(stored, tuple[StressResult, ...])
            elif kind == ReportKind.CONVERGENCE and job.operation == Operation.CONVERGENCE:
                evidence = decode(stored, ConvergenceStudy)
            elif kind == ReportKind.MUTATION and job.operation == Operation.MUTATION:
                evidence = decode(stored, MutationCampaign)
            else:
                raise DomainValidationError("Report kind does not match the stored computation")
        report = make_report(
            kind,
            evidence,
            report_id=key,
            generated=now,
            is_synthetic=synthetic,
            interpretation=interpretation,
        )
        payload = Document(
            json.dumps({"json": report.json(), "html": report.html()}, allow_nan=False)
        )
        return self.objects.put(StoredObject(principal.subject, "report", key, payload, now))
