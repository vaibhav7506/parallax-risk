"""Full synthetic service demonstration through an injected authenticated transport."""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from parallax_risk.application.calibration import CalibrationRunResult
from parallax_risk.application.governance_codec import StoredRecord, encode, record_key
from parallax_risk.application.governance_reports import ReportKind
from parallax_risk.application.service_examples import commands
from parallax_risk.application.wire import decode, value
from parallax_risk.application.workflows import COMMANDS, Command, Operation, walk
from parallax_risk.common.canonical import JsonValue
from parallax_risk.common.errors import InfrastructureError
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario
from parallax_risk.domain.governance.contracts import (
    Approval,
    Decision,
    Document,
    Finding,
    Model,
    ModelStatus,
    Version,
)
from parallax_risk.domain.market.snapshot import MarketSnapshot
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.validation.contracts import Severity
from parallax_risk.domain.validation.mutation import MutationCampaign


class Transport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        payload: JsonValue = None,
        *,
        idempotency_key: str | None = None,
    ) -> JsonValue: ...


def _data(response: JsonValue) -> dict[str, JsonValue]:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        raise InfrastructureError("Unexpected service response")
    return data


def demonstrate(
    client: Transport,
    subject: str,
    *,
    paths: int = 4,
    progress: Callable[[str], None] = lambda _: None,
) -> dict[str, JsonValue]:
    """Register, calibrate, compute, validate, record findings, replay and report.

    Run IDs are fresh; numerical inputs/seeds/as-of dates are deterministic. The
    authenticated subject must hold all five roles for this research demonstration.
    """
    label = "synthetic-phase12-" + uuid4().hex[:12]
    model_id, version_id = label, label + "-v1"
    now = datetime.now(UTC)
    inventory = Model(
        model_id,
        "Synthetic service XVA",
        "research_xva",
        subject,
        "Synthetic end-to-end demonstration",
        ModelStatus.DEVELOPMENT,
        version_id,
        "Existing additive research XVA and CCR/validation engines",
        ("Four paths do not establish tail accuracy", "Research use only"),
        "Synthetic research; no regulatory claim",
        92,
        None,
        now.date() + timedelta(days=92),
    )
    version = Version(
        version_id,
        model_id,
        "0.12.0",
        "Parallax Risk 0.12.0; no source commit supplied",
        Document.of({"synthetic": True, "paths": paths}),
        Document.of({"seed": 20261001}),
        now,
    )
    refs: list[tuple[str, str]] = []

    def save(record: StoredRecord) -> None:
        client.request(
            "POST",
            "/v1/governance",
            {
                "document": encode(record).value(),
                "expected_revision": 0,
                "reason": "Synthetic Phase 12 service demonstration",
            },
        )
        refs.append(record_key(record))

    save(inventory)
    save(version)
    registered: set[tuple[str, str]] = set()

    def retain(command: Command) -> None:
        for node in walk(command):
            if isinstance(node, PortfolioSnapshot):
                kind, key = "portfolios", str(node.portfolio_id) + ":" + str(node.version)
            elif isinstance(node, MarketSnapshot):
                kind, key = "market/snapshots", str(node.snapshot_id) + ":" + str(node.version)
            elif isinstance(node, ConditionalMarketScenario):
                kind, key = "market/scenarios", node.hash
            else:
                continue
            if (kind, key) not in registered:
                client.request("POST", "/v1/" + kind, {"key": key, "data": value(node)})
                registered.add((kind, key))

    def submit(
        operation: Operation, command: Command, reference: str | None = None
    ) -> tuple[str, dict[str, JsonValue]]:
        retain(command)
        payload: JsonValue = {
            "model_id": model_id,
            "version_id": version_id,
            "is_synthetic": True,
            "payload": value(command),
            "calibration_job": reference,
        }
        result = _data(
            client.request("POST", "/v1/" + operation.value, payload, idempotency_key=uuid4().hex)
        )
        job_id = result.get("job_id")
        if not isinstance(job_id, str):
            raise InfrastructureError("Missing job identifier")
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = _data(client.request("GET", "/v1/runs/" + job_id)).get("status")
            if state == "failed":
                raise InfrastructureError("Synthetic workflow failed: " + operation.value)
            if state == "succeeded":
                return job_id, _data(client.request("GET", "/v1/runs/" + job_id + "/result"))
            time.sleep(1.0)
        raise InfrastructureError("Synthetic workflow wait budget elapsed")

    initial = commands(paths)
    calibration_id, calibration_result = submit(
        Operation.CALIBRATION, initial[Operation.CALIBRATION]
    )
    calibration_document = calibration_result["result"]
    if not isinstance(calibration_document, dict):
        raise InfrastructureError("Invalid calibration result")
    fitted = decode(calibration_document["value"], CalibrationRunResult).calibration
    fitted.require_converged()
    inputs = commands(paths, fitted.fitted_parameters)
    jobs: dict[Operation, str] = {Operation.CALIBRATION: calibration_id}
    results: dict[Operation, dict[str, JsonValue]] = {Operation.CALIBRATION: calibration_result}
    for op, command in inputs.items():
        if op == Operation.CALIBRATION:
            continue
        linked = (
            calibration_id
            if op
            in (
                Operation.SIMULATION,
                Operation.EXPOSURE,
                Operation.XVA,
                Operation.CAPITAL,
                Operation.COMPARISON,
                Operation.CONVERGENCE,
                Operation.SENSITIVITY,
                Operation.STRESS,
                Operation.UNCERTAINTY,
                Operation.ADVERSARIAL,
            )
            else None
        )
        jobs[op], results[op] = submit(op, command, linked)
        progress(op.value + " succeeded")
    mutation_document = results[Operation.MUTATION]["result"]
    if not isinstance(mutation_document, dict):
        raise InfrastructureError("Invalid mutation result")
    campaign = decode(mutation_document["value"], MutationCampaign)
    misses = sum(not item.detected for item in campaign.evidence)
    save(
        Finding(
            label + "-finding",
            model_id,
            version_id,
            Severity.HIGH,
            "Weak mutation suite leaves seeded faults undetected",
            Document.of({"job_id": jobs[Operation.MUTATION], "misses": misses}),
            subject,
            now.date() + timedelta(days=30),
        )
    )
    save(
        Approval(
            label + "-decision",
            model_id,
            version_id,
            Decision.CONDITIONAL,
            "Synthetic workflow decision; weak-suite finding remains open",
            Document.of({"mutation_job": jobs[Operation.MUTATION]}),
            ("Research-only use; improve detection before broader deployment",),
            subject,
            datetime.now(UTC),
        )
    )
    original = _data(client.request("GET", "/v1/runs/" + jobs[Operation.XVA] + "/input"))
    # Replay exactly the retained financial input, using the same authenticated model/version.
    retained = original["request"]
    if not isinstance(retained, dict):
        raise InfrastructureError("Invalid retained replay input")
    replay_command = decode(retained["payload"], COMMANDS[Operation.XVA])
    replay_id, replay = submit(Operation.XVA, replay_command, calibration_id)
    if results[Operation.XVA]["hash"] != replay["hash"]:
        raise InfrastructureError("Retained-input replay differs")
    report_jobs = {
        ReportKind.TECHNICAL: Operation.COMPARISON,
        ReportKind.COMPARISON: Operation.COMPARISON,
        ReportKind.STRESS: Operation.STRESS,
        ReportKind.CONVERGENCE: Operation.CONVERGENCE,
        ReportKind.MUTATION: Operation.MUTATION,
        ReportKind.LINEAGE: Operation.XVA,
    }
    report_ids: list[JsonValue] = []
    for kind in ReportKind:
        key = label + "-" + kind.value
        client.request(
            "POST",
            "/v1/reports",
            {
                "key": key,
                "kind": kind.value,
                "source_job": None if kind == ReportKind.GOVERNANCE else jobs[report_jobs[kind]],
                "governance_keys": value(tuple(refs)) if kind == ReportKind.GOVERNANCE else [],
                "governance_synthetic": True if kind == ReportKind.GOVERNANCE else None,
                "interpretation": (
                    "Explicit synthetic research; findings and failed checks remain visible"
                ),
            },
        )
        report_ids.append(key)
    return {
        "is_synthetic": True,
        "model_id": model_id,
        "version_id": version_id,
        "jobs": {op.value: job for op, job in jobs.items()},
        "report_ids": report_ids,
        "replay_job": replay_id,
        "replay_equal": True,
        "weak_mutation_misses": misses,
        "calibration_parameters": value(fitted.fitted_parameters),
        "registered_inputs": len(registered),
    }
