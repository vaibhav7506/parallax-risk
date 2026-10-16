"""Live PostgreSQL migration, append-only, rollback and racing-write verification."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from parallax_risk.application.governance import ConflictError, Governance, Reference, Snapshot
from parallax_risk.application.governance_codec import encode
from parallax_risk.application.governance_examples import example
from parallax_risk.application.governance_reports import ReportKind
from parallax_risk.common.errors import InfrastructureError
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from parallax_risk.infrastructure.persistence.governance import PostgresGovernance, heads
from parallax_risk.infrastructure.persistence.migrate import migrate
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution
from tests.unit.test_governance import LATER, MODEL, NOW, VERSION, save

pytestmark = pytest.mark.postgres


@pytest.fixture
def database():
    url = os.environ.get("PARALLAX_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("No isolated PostgreSQL URL configured; live verification not inferred")
    schema = "parallax_phase11_" + uuid4().hex
    owner = create_engine(url, hide_parameters=True)
    with owner.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={
            "options": f"-c search_path={schema} -c statement_timeout=15000 -c lock_timeout=10000"
        },
    )
    try:
        with engine.begin() as connection:
            migrate(connection)
        yield engine
    finally:
        engine.dispose()
        # Only this test's UUID-named schema in the explicitly isolated test DB.
        with owner.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        owner.dispose()


def test_actual_upgrade_repeat_downgrade_and_reupgrade(database):
    assert set(inspect(database).get_table_names()) == {
        "alembic_version",
        "governance_heads",
        "governance_events",
    }
    with database.begin() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0011"
        )
        migrate(connection)
    governance = Governance(PostgresGovernance(database))
    save(governance, MODEL)
    with database.begin() as connection:
        with pytest.raises(ValueError, match="opt-in"):
            migrate(connection, downgrade_to_base=True)
        migrate(connection, downgrade_to_base=True, allow_destructive=True)
    assert set(inspect(database).get_table_names()) == {"alembic_version"}
    with database.begin() as connection:
        migrate(connection)
    assert governance.repository.get("model", "model") is None


def test_actual_read_history_immutability_and_stale_write(database):
    repository = PostgresGovernance(database)
    governance = Governance(repository)
    first = save(governance, MODEL)
    second = save(governance, replace(MODEL, owner="new owner"), 1)
    assert repository.get("model", "model") == second
    assert repository.history("model", "model") == (first, second)
    assert repository.history("model", "missing") == ()
    with pytest.raises(ConflictError):
        repository.save(Snapshot(MODEL, 2, "actor", LATER, "stale"), 1, ())
    assert len(repository.history("model", "model")) == 2
    save(governance, VERSION)
    with pytest.raises(InfrastructureError):
        repository.save(
            Snapshot(replace(VERSION, label="tamper"), 2, "actor", LATER, "invalid"), 1, ()
        )
    assert repository.get("version", "version").record == VERSION


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE governance_events SET reason = 'tampered'",
        "DELETE FROM governance_events",
        "UPDATE governance_heads SET revision = 7",
        "UPDATE governance_heads SET entity_id = 'renamed'",
        "INSERT INTO governance_heads VALUES ('model','orphan',1)",
        "INSERT INTO governance_heads VALUES ('unknown','bad',1)",
        "INSERT INTO governance_heads VALUES ('model','bad',2)",
    ],
)
def test_database_rejects_history_mutation_or_invalid_heads(database, sql):
    governance = Governance(PostgresGovernance(database))
    first = save(governance, MODEL)
    with pytest.raises(SQLAlchemyError), database.begin() as connection:
        connection.execute(text(sql))
    assert governance.repository.history("model", "model") == (first,)


def test_failed_event_append_rolls_back_head_advancement(database):
    governance = Governance(PostgresGovernance(database))
    first = save(governance, MODEL)

    def fail_event(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO governance_events"):
            raise OperationalError("SECRET SQL", {}, Exception("SECRET CREDENTIAL"))

    event.listen(database, "before_cursor_execute", fail_event)
    try:
        with pytest.raises(InfrastructureError) as error:
            save(governance, replace(MODEL, owner="new"), 1)
        assert "SECRET" not in str(error.value)
    finally:
        event.remove(database, "before_cursor_execute", fail_event)
    assert governance.repository.get("model", "model") == first
    assert governance.repository.history("model", "model") == (first,)


def test_stale_reference_aborts_entire_new_record(database):
    repository = PostgresGovernance(database)
    governance = Governance(repository)
    first = save(governance, MODEL)
    save(governance, replace(MODEL, owner="changed"), 1)
    with pytest.raises(ConflictError):
        repository.save(Snapshot(VERSION, 1, "actor", LATER, "version"), 0, (Reference.of(first),))
    assert repository.get("version", "version") is None
    with database.connect() as connection:
        assert (
            connection.execute(select(heads.c.revision).where(heads.c.kind == "version")).first()
            is None
        )


def test_two_concurrent_writers_have_exactly_one_winner(database):
    repository = PostgresGovernance(database)
    save(Governance(repository), MODEL)
    barrier = Barrier(2)

    def write(owner):
        candidate = Snapshot(replace(MODEL, owner=owner), 2, owner, LATER, "concurrent CAS")
        barrier.wait(timeout=10)
        try:
            repository.save(candidate, 1, ())
            return "saved"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(write, ("first", "second")))
    assert outcomes == ["conflict", "saved"]
    assert tuple(value.revision for value in repository.history("model", "model")) == (1, 2)


def test_duplicate_new_identifier_conflict_preserves_first_event(database):
    repository = PostgresGovernance(database)
    first = save(Governance(repository), MODEL)
    with pytest.raises(ConflictError):
        repository.save(first, 0, ())
    assert repository.history("model", "model") == (first,)


@pytest.mark.parametrize("operation", ["get", "history", "save"])
def test_adapter_sanitizes_database_failures(database, operation):
    repository = PostgresGovernance(database)
    with database.begin() as connection:
        migrate(connection, downgrade_to_base=True, allow_destructive=True)
    with pytest.raises(InfrastructureError) as error:
        if operation == "save":
            repository.save(Snapshot(MODEL, 1, "actor", NOW, "reason"), 0, ())
        else:
            getattr(repository, operation)("model", "model")
    assert "postgresql" not in str(error.value) and "SELECT" not in str(error.value)


def test_seven_actual_reports_and_governed_xva_roundtrip(database, tmp_path):
    repository = PostgresGovernance(database)
    reports = example(Governance(repository), ScipyLeastSquares(), ScipyDifferentialEvolution())
    assert {report.kind for report in reports} == set(ReportKind)
    for report in reports:
        assert report.is_synthetic
        target = tmp_path / f"{report.kind.value}.json"
        target.write_text(report.json(), encoding="utf-8")
        assert target.read_text(encoding="utf-8") == report.json()
        assert report.evidence.hash in report.html()
    lineage = repository.get("lineage", "synthetic-phase11-run")
    assert lineage.record.code_revision is None
    assert lineage.record.calibration_id is None
    assert len(lineage.record.result_hash) == 64
    assert decode_record(repository, "lineage", "synthetic-phase11-run") == lineage.record
    mutation = next(report for report in reports if report.kind == ReportKind.MUTATION)
    assert '"detected":1' in mutation.evidence.text
    assert '"executed":15' in mutation.evidence.text
    # A repeated demo cannot overwrite its immutable identifiers.
    with pytest.raises(ConflictError):
        example(Governance(repository), ScipyLeastSquares(), ScipyDifferentialEvolution())


def decode_record(repository, kind, entity_id):
    from parallax_risk.application.governance_codec import decode

    return decode(encode(repository.get(kind, entity_id).record))


def test_packaged_frozen_revision_executes_with_alembic_operations(database):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from parallax_risk.infrastructure.persistence.migrations.versions import phase11_governance

    with database.begin() as connection:
        migrate(connection, downgrade_to_base=True, allow_destructive=True)
        with Operations.context(MigrationContext.configure(connection)):
            phase11_governance.upgrade()
        assert "governance_events" in inspect(connection).get_table_names()
        with Operations.context(MigrationContext.configure(connection)):
            phase11_governance.downgrade()
        assert "governance_events" not in inspect(connection).get_table_names()
        migrate(connection)


@pytest.mark.parametrize("tamper", ["digest", "identity"])
def test_privileged_tamper_is_detected_when_reading_evidence(database, tamper):
    repository = PostgresGovernance(database)
    save(Governance(repository), MODEL)
    with database.begin() as connection:
        # A DB administrator can bypass protections; this test uses only its disposable schema.
        connection.execute(
            text("ALTER TABLE governance_events DISABLE TRIGGER governance_event_immutable")
        )
        if tamper == "digest":
            connection.execute(
                text("UPDATE governance_events SET content_hash = :digest"), {"digest": "b" * 64}
            )
        else:
            document = encode(replace(MODEL, model_id="other"))
            connection.execute(
                text("UPDATE governance_events SET document=:document, content_hash=:digest"),
                {"document": document.text, "digest": document.hash},
            )
        connection.execute(
            text("ALTER TABLE governance_events ENABLE TRIGGER governance_event_immutable")
        )
    with pytest.raises(InfrastructureError):
        repository.get("model", "model")
