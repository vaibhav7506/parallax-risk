# PostgreSQL scope and lifecycle

`src/parallax_risk/application/ports.py` supplies ConnectivityProbe.
`src/parallax_risk/infrastructure/persistence/database.py` implements
PostgresConnectivity using an explicitly created SQLAlchemy engine, bounded pool/
connect/statement timeouts, real SELECT 1 and sanitized errors.

There are **no tables, governance entities or migration revisions**. Alembic is a
declared later dependency, not an existing schema. Connectivity is not proof of
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
