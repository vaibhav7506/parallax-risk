"""Governance contract, state-machine, monitoring and evidence serialization tests."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from parallax_risk.application.governance import (
    ConflictError,
    Governance,
    Reference,
    Snapshot,
    validate_write,
)
from parallax_risk.application.governance_codec import decode, encode, record_key
from parallax_risk.application.governance_reports import Report, ReportKind, make_report
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain.governance.contracts import (
    Approval,
    Decision,
    Document,
    Finding,
    FindingStatus,
    Limitation,
    Lineage,
    Model,
    ModelStatus,
    Version,
    finding_transition,
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
from parallax_risk.domain.validation.contracts import Severity

NOW = datetime(2026, 10, 2, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)
HASH = "a" * 64
DOC = Document.of({"source": "synthetic test evidence"})
MODEL = Model(
    "model",
    "Model",
    "research",
    "owner",
    "test",
    ModelStatus.DEVELOPMENT,
    "version",
    "method",
    ("restricted",),
    "research only",
    90,
    None,
    date(2027, 1, 2),
)
VERSION = Version("version", "model", "1", "code.py:entry; no revision supplied", DOC, DOC, NOW)
FINDING = Finding(
    "finding", "model", "version", Severity.HIGH, "failed check", DOC, "owner", date(2026, 11, 2)
)
POLICY = Policy(
    "policy",
    "model",
    "version",
    MonitorKind.CVA,
    "CVA",
    "USD",
    Statistic.ABSOLUTE_CHANGE,
    2.0,
    Severity.MEDIUM,
    "synthetic declared threshold",
)
BEFORE = Observation("CVA", "USD", -10.0, HASH, HASH, NOW)
AFTER = replace(BEFORE, value=-13.0, timestamp=LATER)
EVALUATION = Evaluation("evaluation", POLICY, BEFORE, AFTER)
ALERT = Alert("alert", "model", "version", "evaluation", Severity.MEDIUM, AlertState.OPEN, DOC)
LINEAGE = Lineage(
    "run",
    "model",
    "version",
    None,
    HASH,
    HASH,
    HASH,
    None,
    1,
    DOC,
    (),
    NOW,
    DOC,
    HASH,
    ("Synthetic test; absent calibration and source revision",),
)
APPROVAL = Approval(
    "approval",
    "model",
    "version",
    Decision.CONDITIONAL,
    "research decision",
    DOC,
    ("research only",),
    "declared authority",
    NOW,
)
LIMITATION = Limitation(
    "limitation", "model", "version", "no MPOR closeout", (HASH,), "research", ("restrict use",)
)
RECORDS = (MODEL, VERSION, FINDING, APPROVAL, LIMITATION, LINEAGE, POLICY, EVALUATION, ALERT)


class Memory:
    """Test double; PostgreSQL claims come only from the separate live suite."""

    def __init__(self):
        self.values = {}
        self.events = {}

    def get(self, kind, entity_id):
        return self.values.get((kind, entity_id))

    def history(self, kind, entity_id):
        return tuple(self.events.get((kind, entity_id), ()))

    def save(self, snapshot, expected_revision, references):
        validate_write(snapshot, expected_revision, references)
        key = record_key(snapshot.record)
        current = self.values.get(key)
        if (current.revision if current else 0) != expected_revision:
            raise ConflictError("stale test snapshot")
        for reference in references:
            current = self.get(reference.kind, reference.entity_id)
            if current is None or current.revision != reference.revision:
                raise ConflictError("stale test reference")
        self.values[key] = snapshot
        self.events.setdefault(key, []).append(snapshot)


@pytest.fixture
def governance():
    workflow = Governance(Memory())
    save(workflow, MODEL)
    save(workflow, VERSION)
    return workflow


def save(governance, record, revision=0, timestamp=LATER):
    return governance.record(
        record,
        expected_revision=revision,
        actor="test-actor",
        timestamp=timestamp,
        reason="synthetic test",
    )


@pytest.mark.parametrize("record", RECORDS)
def test_roundtrip_revalidates_all_record_types_and_is_immutable(record):
    assert decode(encode(record)) == record
    assert encode(decode(encode(record))).hash == encode(record).hash
    with pytest.raises(FrozenInstanceError):
        setattr(record, fields(record)[0].name, "changed")


@pytest.mark.parametrize(
    "text", ["[]", "null", '{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', "{", ""]
)
def test_evidence_rejects_malformed_nonfinite_or_ambiguous_json(text):
    with pytest.raises((DomainValidationError, ArithmeticError)):
        Document(text)


def test_document_fingerprint_and_copy_semantics():
    first = Document('{"b":2, "a":{"x":1}}')
    second = Document('{"a":{"x":1},"b":2}')
    assert first == second and first.hash == second.hash
    value = first.value()
    value["a"]["x"] = 7
    assert first.value()["a"]["x"] == 1
    assert Document.of({"x": "1"}).hash != Document.of({"x": 1}).hash


INVALID = [
    (MODEL, "model_id", ""),
    (MODEL, "status", "active"),
    (MODEL, "limitations", []),
    (MODEL, "limitations", ("x", "x")),
    (MODEL, "validation_frequency_days", True),
    (MODEL, "validation_frequency_days", 0),
    (MODEL, "next_review", NOW),
    (MODEL, "last_validation", date(2027, 1, 2)),
    (VERSION, "configuration", {}),
    (VERSION, "created", NOW.replace(tzinfo=None)),
    (FINDING, "severity", "high"),
    (FINDING, "remediation", ""),
    (FINDING, "status", FindingStatus.REMEDIATING),
    (FINDING, "closure_evidence", DOC),
    (FINDING, "status", FindingStatus.CLOSED),
    (APPROVAL, "conditions", ()),
    (APPROVAL, "decision", Decision.APPROVE),
    (LIMITATION, "affected_portfolios", ("wrong",)),
    (LIMITATION, "compensating_controls", ()),
    (LINEAGE, "seed", 2**64),
    (LINEAGE, "seed", -1),
    (LINEAGE, "seed", True),
    (LINEAGE, "code_revision", ""),
    (LINEAGE, "calibration_id", ""),
    (LINEAGE, "csa_versions", ("wrong",)),
    (LINEAGE, "assumptions", ()),
    (POLICY, "threshold", -1),
    (POLICY, "threshold", float("inf")),
    (POLICY, "statistic", "increase"),
    (POLICY, "kind", "cva_movement"),
    (POLICY, "kind", MonitorKind.VALIDATION),
    (BEFORE, "value", float("nan")),
    (ALERT, "state", AlertState.RESOLVED),
    (ALERT, "resolution_evaluation_id", "recovery"),
    (EVALUATION, "policy", {}),
    (EVALUATION, "current", BEFORE),
    (EVALUATION, "current", replace(AFTER, unit="EUR")),
    (EVALUATION, "current", replace(AFTER, comparison_scope_hash="b" * 64)),
]


@pytest.mark.parametrize("record,field,value", INVALID)
def test_invalid_domain_values_are_rejected(record, field, value):
    with pytest.raises((DomainValidationError, ArithmeticError)):
        replace(record, **{field: value})


@pytest.mark.parametrize("kind", list(MonitorKind))
def test_all_seven_monitor_types_retain_evidence_and_use_explicit_units(kind):
    policy = POLICY if kind == MonitorKind.VALIDATION else replace(POLICY, kind=kind)
    before, after = BEFORE, AFTER
    if kind == MonitorKind.VALIDATION:
        policy = replace(POLICY, kind=kind, unit="count", statistic=Statistic.LEVEL)
        before = replace(BEFORE, unit="count", value=0)
        after = replace(AFTER, unit="count", value=3)
    result = Evaluation("evaluation", policy, before, after)
    assert result.triggered
    assert result.baseline.evidence_hash == HASH
    assert decode(encode(result)) == result


@pytest.mark.parametrize(
    "statistic,expected",
    [
        (Statistic.ABSOLUTE_CHANGE, 3),
        (Statistic.INCREASE, -3),
        (Statistic.DECREASE, 3),
        (Statistic.LEVEL, -13),
    ],
)
def test_monitor_direction_and_signed_cva(statistic, expected):
    result = replace(EVALUATION, policy=replace(POLICY, statistic=statistic))
    assert result.statistic == expected
    assert result.triggered == (expected > 2)
    assert not replace(EVALUATION, current=replace(AFTER, value=-12)).triggered


@pytest.mark.parametrize("value", [-1, 1.5])
def test_validation_monitor_rejects_noncounts(value):
    policy = replace(POLICY, kind=MonitorKind.VALIDATION, unit="count", statistic=Statistic.LEVEL)
    with pytest.raises(DomainValidationError):
        Evaluation(
            "evaluation",
            policy,
            replace(BEFORE, unit="count", value=value),
            replace(AFTER, unit="count", value=3),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema=2),
        lambda d: d.update(schema=True),
        lambda d: d.update(kind="unknown"),
        lambda d: d.update(extra=1),
        lambda d: d.pop("record"),
        lambda d: d["record"].update(__type__="fake"),
        lambda d: d["record"].update(configuration={"text": "{}"}),
    ],
)
def test_codec_rejects_unknown_schema_and_forged_types(mutation):
    value = encode(VERSION).value()
    mutation(value)
    with pytest.raises(DomainValidationError):
        decode(Document.of(value))


def test_finding_lifecycle_requires_remediation_and_closure_evidence(governance):
    first = save(governance, FINDING)
    remediating = replace(
        FINDING, status=FindingStatus.REMEDIATING, remediation="Improve suite; no success inferred"
    )
    second = save(governance, remediating, 1)
    closed = replace(remediating, status=FindingStatus.CLOSED, closure_evidence=DOC)
    third = save(governance, closed, 2)
    assert governance.repository.history("finding", "finding") == (first, second, third)
    with pytest.raises(DomainValidationError):
        save(governance, FINDING, 3)
    with pytest.raises(DomainValidationError):
        finding_transition(FINDING, replace(remediating, owner="other"))
    with pytest.raises(DomainValidationError):
        finding_transition(FINDING, closed)


def test_inventory_transitions_and_decisions_remain_distinct(governance):
    save(governance, APPROVAL)
    assert governance.repository.get("model", "model").record.status == ModelStatus.DEVELOPMENT
    validation = replace(MODEL, status=ModelStatus.VALIDATION)
    save(governance, validation, 1)
    active = replace(validation, status=ModelStatus.ACTIVE)
    save(governance, active, 2)
    save(governance, replace(active, status=ModelStatus.RETIRED), 3)
    with pytest.raises(DomainValidationError):
        save(governance, active, 4)


@pytest.mark.parametrize("record", [VERSION, APPROVAL, LIMITATION, LINEAGE, POLICY, EVALUATION])
def test_immutable_records_never_accept_overwrites(governance, record):
    if record == VERSION:
        with pytest.raises(ConflictError):
            save(governance, replace(VERSION, label="2"), 1)
        return
    if record == EVALUATION:
        save(governance, POLICY)
    save(governance, record)
    with pytest.raises(ConflictError):
        save(governance, record, 1)


def test_stale_reference_missing_scope_and_backwards_audit(governance):
    with pytest.raises(ConflictError):
        save(governance, MODEL, 0)
    with pytest.raises(DomainValidationError):
        save(governance, replace(FINDING, model_id="missing"))
    other = replace(MODEL, model_id="other")
    save(governance, other)
    with pytest.raises(DomainValidationError):
        save(governance, replace(FINDING, model_id="other"))
    with pytest.raises(DomainValidationError):
        save(governance, MODEL, 1, NOW)
    with pytest.raises(DomainValidationError):
        save(governance, replace(APPROVAL, decided=LATER + timedelta(days=1)))
    with pytest.raises(DomainValidationError):
        save(governance, replace(VERSION, version_id="future", created=LATER + timedelta(days=1)))
    with pytest.raises(DomainValidationError):
        save(governance, replace(LINEAGE, timestamp=LATER + timedelta(days=1)))
    with pytest.raises(DomainValidationError):
        save(governance, replace(MODEL, model_id="new", status=ModelStatus.ACTIVE))


def test_alert_acknowledgement_and_recovery_preserve_opening_evidence(governance):
    save(governance, POLICY)
    save(governance, EVALUATION)
    save(governance, ALERT)
    acknowledged = replace(ALERT, state=AlertState.ACKNOWLEDGED)
    save(governance, acknowledged, 1)
    recovered = replace(
        EVALUATION,
        evaluation_id="recovery",
        current=replace(AFTER, value=-11, timestamp=LATER + timedelta(hours=1)),
    )
    save(governance, recovered, timestamp=LATER + timedelta(hours=2))
    resolved = replace(acknowledged, state=AlertState.RESOLVED, resolution_evaluation_id="recovery")
    save(governance, resolved, 2, LATER + timedelta(hours=2))
    assert len(governance.repository.history("alert", "alert")) == 3
    with pytest.raises(DomainValidationError):
        save(governance, ALERT, 3, LATER + timedelta(hours=2))


@pytest.mark.parametrize(
    "problem",
    [
        "missing-policy",
        "wrong-policy",
        "future",
        "not-triggered",
        "wrong-severity",
        "new-ack",
        "changed-evidence",
        "skip-ack",
        "not-recovered",
    ],
)
def test_invalid_monitoring_and_alert_transitions(governance, problem):
    if problem == "missing-policy":
        with pytest.raises(DomainValidationError):
            save(governance, EVALUATION)
        return
    save(governance, POLICY)
    if problem == "wrong-policy":
        with pytest.raises(DomainValidationError):
            save(governance, replace(EVALUATION, policy=replace(POLICY, threshold=3)))
        return
    if problem == "future":
        with pytest.raises(DomainValidationError):
            save(
                governance,
                replace(EVALUATION, current=replace(AFTER, timestamp=LATER + timedelta(hours=1))),
            )
        return
    if problem == "not-triggered":
        save(governance, replace(EVALUATION, current=replace(AFTER, value=-11)))
    else:
        save(governance, EVALUATION)
    if problem in ("not-triggered", "wrong-severity", "new-ack"):
        record = (
            replace(ALERT, severity=Severity.CRITICAL)
            if problem == "wrong-severity"
            else replace(ALERT, state=AlertState.ACKNOWLEDGED)
            if problem == "new-ack"
            else ALERT
        )
        with pytest.raises(DomainValidationError):
            save(governance, record)
        return
    save(governance, ALERT)
    if problem == "not-recovered":
        save(governance, replace(ALERT, state=AlertState.ACKNOWLEDGED), 1)
        with pytest.raises(DomainValidationError):
            save(
                governance,
                replace(ALERT, state=AlertState.RESOLVED, resolution_evaluation_id="evaluation"),
                2,
            )
        return
    record = (
        replace(ALERT, evidence=Document.of({"other": "evidence"}), state=AlertState.ACKNOWLEDGED)
        if problem == "changed-evidence"
        else replace(ALERT, state=AlertState.RESOLVED, resolution_evaluation_id="evaluation")
    )
    with pytest.raises(DomainValidationError):
        save(governance, record, 1)


def test_write_boundary_checks_and_strict_types():
    snapshot = Snapshot(MODEL, 1, "actor", NOW, "reason")
    reference = Reference.of(snapshot)
    with pytest.raises(DomainValidationError):
        validate_write(snapshot, 1, ())
    with pytest.raises(DomainValidationError):
        validate_write(snapshot, 0, (reference, reference))
    with pytest.raises(DomainValidationError):
        validate_write({}, 0, ())
    with pytest.raises(DomainValidationError):
        record_key({})


def test_governed_run_guards_and_explicit_optional_metadata(governance):
    from parallax_risk.application.governed_risk import GovernedXva
    from tests.fixtures.xva import experiment, revaluation

    runner = GovernedXva(revaluation(), governance)
    case = experiment(paths=4)
    arguments = {
        "model_id": "model",
        "version_id": "version",
        "actor": "test",
        "recorded": LATER,
        "calibration_id": "declared-calibration",
        "code_revision": "declared-source-ref",
    }
    with pytest.raises(DomainValidationError):
        runner.run({}, **arguments)
    with pytest.raises(DomainValidationError):
        runner.run(case, **(arguments | {"version_id": "missing"}))
    with pytest.raises(DomainValidationError):
        runner.run(case, **(arguments | {"model_id": "other"}))
    with pytest.raises(DomainValidationError):
        runner.run(case, **(arguments | {"recorded": case.run.timestamp - timedelta(seconds=1)}))
    run = runner.run(case, **arguments)
    assert run.lineage.record.code_revision == "declared-source-ref"
    assert run.lineage.record.calibration_id == "declared-calibration"
    assert run.lineage.record.portfolio_hash == case.book.snapshot_hash
    assert run.lineage.record.seed == case.request.sequence.key.seed
    with pytest.raises(DomainValidationError):
        runner.run(case, **arguments)
    assert governance.repository.get("lineage", str(case.run.run_id)) == run.lineage


def test_invalid_initial_finding_and_foreign_active_version(governance):
    with pytest.raises(DomainValidationError):
        replace(FINDING, status=FindingStatus.CLOSED, remediation="attempted close")
    closed = replace(
        FINDING, status=FindingStatus.CLOSED, remediation="fixed", closure_evidence=DOC
    )
    with pytest.raises(DomainValidationError):
        save(governance, closed)
    save(governance, replace(MODEL, model_id="other"))
    save(governance, replace(VERSION, model_id="other", version_id="other-version"))
    save(governance, replace(MODEL, status=ModelStatus.VALIDATION), 1)
    with pytest.raises(DomainValidationError):
        save(governance, replace(MODEL, status=ModelStatus.ACTIVE, version="other-version"), 2)
    assert decode(encode(replace(MODEL, last_validation=date(2026, 1, 2)))).last_validation == date(
        2026, 1, 2
    )
    assert decode(encode(replace(LINEAGE, seed=None))).seed is None


def test_persistence_and_migrations_reject_nonpostgres_engines():
    from sqlalchemy import create_engine

    from parallax_risk.infrastructure.persistence.governance import PostgresGovernance
    from parallax_risk.infrastructure.persistence.migrate import migrate
    from parallax_risk.infrastructure.persistence.migrations import env

    engine = create_engine("sqlite:///:memory:")
    try:
        with pytest.raises(DomainValidationError):
            PostgresGovernance(engine)
        with engine.begin() as connection:
            with pytest.raises(ValueError):
                migrate(connection)
            with pytest.raises(ValueError):
                migrate(connection, allow_destructive=1)
    finally:
        engine.dispose()
    with pytest.raises((ValueError, AttributeError)):
        env.run()


@pytest.mark.parametrize("kind", list(ReportKind))
def test_reports_reject_wrong_evidence_types(kind):
    with pytest.raises(DomainValidationError):
        make_report(
            kind,
            {},
            report_id="report",
            generated=NOW,
            is_synthetic=True,
            interpretation="caller interpretation",
        )


def test_report_escapes_html_and_contains_recoverable_evidence():
    lineage = replace(LINEAGE, assumptions=("<script>alert('x')</script>",))
    report = make_report(
        ReportKind.LINEAGE,
        lineage,
        report_id="report",
        generated=NOW,
        is_synthetic=True,
        interpretation="<img src=x onerror=alert(1)>",
    )
    rendered = report.html()
    assert "<script>" not in rendered and "<img" not in rendered
    assert "&lt;script&gt;" in rendered
    assert report.evidence.hash in rendered
    assert report.json() == report.json() and report.html() == report.html()
    assert report.document.value()["evidence_hash"] == report.evidence.hash
    with pytest.raises(DomainValidationError):
        replace(report, is_synthetic=1)
    with pytest.raises(DomainValidationError):
        make_report(
            "lineage",
            lineage,
            report_id="report",
            generated=NOW,
            is_synthetic=True,
            interpretation="reason",
        )
    assert isinstance(report, Report)
