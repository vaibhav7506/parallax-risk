# Your first governance report run

Use the installed development environment and a fresh isolated PostgreSQL database.
Explicitly set PARALLAX_DATABASE_URL to its PostgreSQL/psycopg URL; the library does
not load .env. Do not point this demonstration at production data.

```sh
python scripts/migrate_governance.py
python scripts/demo_governance.py --output artifacts/local/phase11/reports
```

The migration upgrades to 0011; repeat upgrade is safe. The demo creates fixed
synthetic inventory/version/finding/decision/limitation/monitor records and invokes
actual existing XVA, validation and mutation engines. It saves mandatory governed
run lineage and writes seven HTML/JSON report pairs. Open governance_summary.html
and mutation_test.html to inspect the explicitly conditional research decision and
retained weak-suite mutation misses. Input/record/report times are explicitly
synthetic fixed timestamps, not the wall clock.

A second demo in the same schema fails on immutable identifiers. Use a new
explicitly isolated database/schema for replay; do not erase production records.
For controlled schema reversal, migrate(connection, downgrade_to_base=True,
allow_destructive=True) requires an explicitly owned connection and removes all
governance data in its selected schema. It is not a normal release rollback plan.

Windows project-scoped Docker verification:

```powershell
./scripts/verify_phase11.ps1 -Focused
./scripts/verify_phase11.ps1
./scripts/cleanup_docker.ps1 -Phase 11
```

Both verification modes use their own disposable stack and cleanup in finally.
The full mode also builds/checks the installed Linux wheel and executes the whole
Windows/Linux suite. A skipped PostgreSQL test is not live database verification;
read the [actual Phase 11 report](../validation/phase-11.md) for execution status.
[Workflow](../workflows/GOVERNANCE_WORKFLOW.md), [methodology](../methodology/GOVERNANCE.md).
