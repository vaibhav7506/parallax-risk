# PostgreSQL scope and lifecycle

Release 0.12.0 adds immutable owned service objects and durable jobs in revision 0012. Financial results remain pure values in library calls; service successes retain exact input/result documents and registered-model lineage. Service readiness checks both connectivity and revision 0012. [Current operations](SERVICE.md).

## Connectivity and earlier phase scopes

`src/parallax_risk/application/ports.py` supplies ConnectivityProbe.
`src/parallax_risk/infrastructure/persistence/database.py` implements
PostgresConnectivity using an explicitly created SQLAlchemy engine, bounded pool/
connect/statement timeouts, real SELECT 1 and sanitized errors.

Phase 11 adds **governance_heads, governance_events and Alembic revision 0011**.
The separate connectivity probe retains its SELECT 1 behavior. Connectivity is not proof of
data integrity, schema readiness, user permissions or high availability.

API lifespan closes its probe on shutdown; CLI check-db closes in finally. `/ready`
can return 503 for unavailable/unconfigured DB while `/health` remains 200.
`tests/integration/test_database_cli.py` checks failures/lifetimes and requires
`PARALLAX_TEST_DATABASE_URL` for its real PostgreSQL case.

Normal Compose stores data in its persistent project volume and publishes no DB
port. Disposable verification projects use distinct volumes and loopback DB port
55432. Remove only those explicitly disposable volumes after test sessions; retain
normal project data. [Docker ownership policy](DOCKER.md) and
[ADR 0006](../decisions/0006-persistence-boundaries.md) explain why.

Phase 5 PortfolioService and cash ledgers remain immutable in-memory values and
synthetic JSON evidence. No portfolio/collateral tables or migration are added;
live PostgreSQL verification still proves operational connectivity only.

Phase 6: Exposure/credit values are immutable in-memory results. No new table/migration or persisted portfolio/default/risk job is added. Database verification remains real connectivity coverage.
See [workflow](../workflows/EXPOSURE_WORKFLOW.md) and [limits](../LIMITATIONS.md).

Phase 7 XVA/risk results remain immutable in-memory values. No table/migration,
persisted job or institutional model approval is added. Live PostgreSQL checks still
verify operational connectivity rather than financial-result persistence.

Phase 8 adds no CCR comparison table or migration. Input/path/configuration
fingerprints and exception flags remain in immutable in-memory results; they are
not persisted risk jobs or governance Findings. Full tests still exercise live
isolated PostgreSQL. [Evidence](../validation/phase-8.md).

## Phase 9 lab scope

Findings, model comparisons, uncertainty bands and stress results are immutable in-memory values in Phase 9. They are not persisted approval/governance aggregates; no migration is added. Live database verification still targets the existing operational foundation.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 applicability

Phase 10 reports remain in memory/JSON; no table or migration is added. The live PostgreSQL check verifies the operational foundation only, not persisted mutation/search/governance aggregates.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).

## Phase 11 explicit schema and repository

Use `python scripts/migrate_governance.py` with explicit PARALLAX_DATABASE_URL to
upgrade the selected PostgreSQL schema. The packaged Alembic composition borrows
a caller-owned connection; constructors/service startup do not migrate. The
head/event repository validates domain documents on read, detects digest/identity
mismatch, locks revision guards and atomically writes each snapshot plus audit.
Append-only triggers/deferred foreign keys preserve ordinary-write history.

Full inputs, calibrated results and financial path buffers are not stored here.
Lineage retains their identities; retain actual source artifacts for replay. Raw
DB administrators remain trusted. Schema upgrades need explicit privileges;
readiness does not check Alembic revision. Destructive base downgrade requires
allow_destructive=True and removes selected governance data; use only disposable
test schemas for reversal verification.

Tests create UUID-named schemas only in PARALLAX_TEST_DATABASE_URL, then drop only
those schemas in finally. Docker verification removes only its owned phase stack;
normal Compose database data is retained. See [ADR 0029](../decisions/0029-governance-persistence.md),
[governance contracts](../methodology/GOVERNANCE.md), [actual results](../validation/phase-11.md).
