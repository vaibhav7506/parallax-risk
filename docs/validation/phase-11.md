# Parallax Risk — Phase 11 implementation and verification

Status: COMPLETE; release 0.11.0. Phase 12 NOT IMPLEMENTED.
Client date: 2026-10-02. Completed exactly Phase 11; Phase 12 has not been started.

Implemented typed research governance inventory/version/finding/decision/limitation,
SQLAlchemy PostgreSQL transactional head/event repositories, frozen Alembic revision
0011, governed XVA lineage, seven scalar monitoring categories, alert transitions,
and seven evidence-only report kinds in HTML/JSON. No financial API, scheduler,
authentication/signature, regulatory approval, PDF or LLM-generated conclusion.

## Verification and failure history

- First unit run: 6 failed, 78 passed, 19 errors. JSON parser arrays were being
  passed to the strict canonicalizer; fixed by freezing parsed arrays locally.
  Prior common canonical contracts were preserved.
- Unit rerun: 103 passed, 2.26s.
- Local operational/architecture run: 1 failed, 121 passed, 1 PostgreSQL skip,
  1 existing Starlette warning, 8.56s. API VersionResponse still declared Phase 10;
  corrected its literal/default to 11.
- Architecture/API rerun: 8 passed, 1 existing warning, 5.16s.
- Live PostgreSQL 18 focused run: 124 passed, 13.34s, including the 103 units,
  17 actual PostgreSQL cases and 4 architecture/package checks. It exercised zero
  schema upgrade, repeated upgrade, explicit destructive downgrade/reupgrade,
  append-only triggers, stale writes/references, rollback, concurrent CAS, sanitized
  database failures and all seven actual reports.
- Extended guard/tamper tests initially had a test-only fixture import mistake:
  1 failed, 125 passed, 10.17s. Corrected workflow to the actual revaluation fixture;
  unit rerun 106 passed, 2.72s. Full suite subsequently covered all 126 new cases.
- Full Windows Python 3.13.2 / isolated native PostgreSQL 18: **1462 passed**,
  **1 existing Starlette/httpx deprecation warning**, **120.74s**. No DB case skipped.
  **98.97130992827482% statement+branch coverage**; 8398 statements, 2198 branches,
  68 missing statements and 41 missing branches; branch-only 98.13466787989081%.
  Coverage is execution evidence, not financial validity. Alembic dynamically loaded
  env/revision modules are conservatively reported at 0% by the package-scoped
  coverage instrumentation even though live migration/Operations tests executed
  their DDL; no exclusions were added to improve the percentage.
- Final Ruff check passed; Ruff format check: 352 files already formatted; strict
  mypy: 139 source files, no issues. All three configured pre-commit hooks passed
  for 211 explicit source/test/script Python files using the project interpreter.
  A first temporary hook config failed because its absolute executable path was
  unquoted across the workspace space; used the project-relative interpreter path.
  The canonical hook configuration remains unchanged; failed log retained.
- Isolated editable install refreshed version 0.11.0. Package build passed with
  Hatchling 1.32.4. The wheel's 140 production Python/typed files, including packaged
  Alembic scripts, match the tested frozen source byte-for-byte.
- Explicit migration CLI upgraded a fresh selected native DB to revision 0011;
  actual demo wrote **7 HTML/JSON pairs (14 files)** using existing numerical engines.
  Fixed synthetic timestamps/IDs and declared conditional decision remain labeled.
- PowerShell Phase 11 verification helper syntax parsed successfully. After the
  authorized Docker repair, image build, health/readiness/version and check-db
  passed. All 140 installed production-file hashes equal the frozen tested source.
- First full Docker-backed Windows attempt: **1461 passed, 1 warning, 1 error,
  129.82s**, 98.58% branch-inclusive coverage. The seven-report test's tmp_path
  setup failed on Windows access to the shared system pytest temporary directory;
  this was not a PostgreSQL or financial assertion failure. Preserved its logs and
  cleanup inventory. The helper now supplies a fresh UUID-named workspace basetemp
  for each Windows invocation. No test or production source was changed.
- Full Windows Python 3.13.2 / isolated Docker PostgreSQL **17.11** rerun:
  **1462 passed, 1 existing warning, 134.68s**; **98.97130992827482%** combined
  coverage with the same 8398 statements, 2198 branches, 68/41 missing counts.
- Full installed-wheel **Linux Python 3.12.14** / isolated PostgreSQL **17.11**:
  **1462 passed, 1 existing Starlette warning, 148.14s**;
  **98.97130992827482%** combined coverage, 8398 statements/2198 branches and
  68/41 missing counts. No PostgreSQL cases skipped. Read-only mounted tests used
  the installed release package, without a PYTHONPATH source override. Development
  dependencies ran as root only in the disposable --rm test container; production
  runtime UID is **10001**. Environment versions and the pip root-user notice are
  retained in the actual logs. This is a local result, not hosted CI evidence.
- Isolated PostgreSQL 17.11 root schema migration/demo passed: revision 0011 and
  **7 HTML/JSON pairs**, including actual numerical evidence and retained mutation
  misses. Health/ready/version/check-db and production source-hash checks passed.
  Retained tested image ID:
  sha256:620af26b629d2de241740941442a27ca1cf1c7d478d1e61d6167e6a0ae11cbb8.
  The final wheel/source archive include completion documentation; the retained
  tested image contains the earlier in-progress README metadata. All 140 production
  files are identical across tested source, image and final wheel/archive. No second
  quantitative test run is claimed for the documentation-only packaging refresh.
- Documentation checker passed: **139 Markdown files, 32 canonical ADRs,
  1295 concrete path references**, valid local links/index reachability. External
  links were syntax-checked only.

Docker was initially stopped. Starting installed Docker Desktop failed on its own
inaccessible dockerInference runtime socket. The scoped verification helper failed
before creating Phase 11 resources; its finally cleanup also could not connect.
The initial unavailable-daemon attempt provides no live Docker preservation result.
An already installed PostgreSQL 18 cluster was created only in ignored project
artifacts on loopback 55433, with disposable synthetic credentials. It was stopped
using its exact owned data directory, then only that checked workspace directory
and temporary password file were removed. Test/migration/demo logs and 14 reports
were retained. No other PostgreSQL service was targeted.

The user authorized limited Docker shared-runtime repair. With Docker Desktop and
backend processes stopped, only Local Docker/run and Local/docker-secrets-engine
IPC directories were renamed to recoverable sibling backups with suffix
parallax-risk-phase11-recovery-e75eaf48247144b1bb6eb3ea70435055. The exact paths and
process/path checks are retained in docker-runtime-repair.json. Docker Desktop
4.83.0 / daemon 29.6.2 restarted successfully; EnableDockerAI remains true.
No settings reset or image/container/volume/cache removal was part of this repair.
Keep these shared runtime backups; they are outside disposable project cleanup.

The first Docker-backed failed test session removed only its two owned verification
containers, default network and disposable postgres_data volume in finally. Its
before/after inventory preserves all **35 unrelated container IDs/names/projects**.
Release images 0.1.0–0.10.0 and the useful new 0.11.0 image, shared layers/build
cache, original database data and saved artifacts remain. No global prune/reset or
arbitrary container file deletion was attempted. The successful rerun also cleaned
its two verification services, default network and disposable volume in finally;
the standalone Linux test container used --rm. Final scoped preview lists zero
containers, networks or disposable volumes. Sorted before/after identities match
for all 35 unrelated containers in both sessions. All ten older release image IDs
match the retained inventory; 0.11.0 is retained too. The normal persistent
parallax-risk database was never selected for cleanup.

## Assumptions and limitations

See [implemented contracts](../methodology/GOVERNANCE.md): declared actors/authority,
caller-owned review/threshold policy, no monitoring scheduler/external alert delivery,
no automatic approval/remediation, no database-admin tamper guarantee, external
calibration reference, retained-input responsibility and explicit null source revision.
Only governed XVA creates a persisted risk run; legacy numerical entry points remain
ungoverned research calls. Prior financial limitations, including default-conditioned
MPOR absence, remain. All required Phase 11 local verification and scoped cleanup
passed. Completed phases are 1–11; Phase 12 has not been started. Historical evidence
and failed-attempt logs are preserved; test coverage does not confer model approval.

## Documentation, architecture and review record

Created **8 Markdown documents**, updated **64**: this report, governance methods,
workflow/tutorial and ADRs 0029–0032 are new. Reviewed all **32 canonical ADRs** and
appended Phase 11 history to every one; ADR 0006 is superseded by 0029 for its
prior no-schema scope, while connectivity and all old history remain. Material
IDs 0001, 0006, 0029–0032: 6. The canonical ledger records Phase 11 COMPLETE,
with 11 completed phases, 31 accepted ADRs and one superseded ADR.

Reviewed/updated README, AGENTS, ROADMAP, CHANGELOG, INDEX, CODEBASE_GUIDE, WORKFLOW,
DOMAIN_MODEL, GLOSSARY, LIMITATIONS, reproducibility, methodology, validation,
testing, architecture, operation/release/config/security and contribution guides.
Corrected obsolete absent-governance/no-table claims, current API release/phase
metadata and active verification-helper references without rewriting historical
reports. **17 historical phase/maintenance/ADR files are byte-identical**.

New terminology: governance snapshot, compare-and-swap revision, reference guard,
owned governance finding, conditional decision, comparison-scope hash, recovery
evaluation and governed run. Quantitative mathematics and old model-version labels
remain unchanged. Decimal Money and binary64 valuation retain different precision
contracts. No dependencies/locks/notebooks or previous numerical equations changed.

Architecture adds inert domain values, injected application lifecycle/codec/report/
governed-run workflows and infrastructure PostgreSQL/Alembic adapters. Scripts own
engine lifetimes. No SQLAlchemy/framework dependency enters domain/application.
Commands verified: Ruff/format/mypy/pre-commit, full Windows/installed-wheel Linux
pytest/coverage, package build, architecture/API/CLI tests, native and Docker-backed
migration/demo, docs checker and PowerShell syntax. The full Phase 11 helper's
Docker build/start/HTTP/check-db/hash/runtime/cleanup commands passed. Focused mode's
syntax was checked; a separate completed focused Docker run is not claimed.

Deferred documents: Phase 12 financial API, authentication, production scale/
monitor scheduling/external notification, PDF and institutional approval guides.
No empty future pages created. Authorized shared Docker repair is complete; its
recoverable runtime-directory backups are retained separately from project resources.

## File manifest

**27 created, 73 updated, 0 removed** against the exact 351-file 0.10.0 baseline.
Detailed before/after hashes, frozen production hashes, environment, coverage,
package integrity and report hashes are retained in ignored artifacts/local/phase11.
Archive digests are kept outside this report to avoid self-referential hashes.
Only four existing production files changed: release/operational metadata in
package init, API app/schema and CLI; all prior financial modules are unchanged.

| Change | File |
|---|---|
| created | `docs/decisions/0029-governance-persistence.md` |
| created | `docs/decisions/0030-governed-risk-lineage.md` |
| created | `docs/decisions/0031-monitoring-alert-transitions.md` |
| created | `docs/decisions/0032-evidence-report-rendering.md` |
| created | `docs/methodology/GOVERNANCE.md` |
| created | `docs/tutorials/10-FIRST-GOVERNANCE-RUN.md` |
| created | `docs/validation/phase-11.md` |
| created | `docs/workflows/GOVERNANCE_WORKFLOW.md` |
| created | `scripts/demo_governance.py` |
| created | `scripts/migrate_governance.py` |
| created | `scripts/verify_phase11.ps1` |
| created | `src/parallax_risk/application/governance.py` |
| created | `src/parallax_risk/application/governance_codec.py` |
| created | `src/parallax_risk/application/governance_examples.py` |
| created | `src/parallax_risk/application/governance_reports.py` |
| created | `src/parallax_risk/application/governed_risk.py` |
| created | `src/parallax_risk/domain/governance/__init__.py` |
| created | `src/parallax_risk/domain/governance/contracts.py` |
| created | `src/parallax_risk/domain/governance/monitoring.py` |
| created | `src/parallax_risk/infrastructure/persistence/governance.py` |
| created | `src/parallax_risk/infrastructure/persistence/migrate.py` |
| created | `src/parallax_risk/infrastructure/persistence/migrations/__init__.py` |
| created | `src/parallax_risk/infrastructure/persistence/migrations/env.py` |
| created | `src/parallax_risk/infrastructure/persistence/migrations/versions/__init__.py` |
| created | `src/parallax_risk/infrastructure/persistence/migrations/versions/phase11_governance.py` |
| created | `tests/integration/test_governance_postgres.py` |
| created | `tests/unit/test_governance.py` |
| updated | `AGENTS.md` |
| updated | `CHANGELOG.md` |
| updated | `CONTRIBUTING.md` |
| updated | `DEVELOPMENT.md` |
| updated | `Makefile` |
| updated | `README.md` |
| updated | `ROADMAP.md` |
| updated | `SECURITY.md` |
| updated | `docker-compose.yml` |
| updated | `docs/CODEBASE_GUIDE.md` |
| updated | `docs/DOMAIN_MODEL.md` |
| updated | `docs/GLOSSARY.md` |
| updated | `docs/INDEX.md` |
| updated | `docs/LIMITATIONS.md` |
| updated | `docs/REPRODUCIBILITY.md` |
| updated | `docs/WORKFLOW.md` |
| updated | `docs/api/ENDPOINTS.md` |
| updated | `docs/api/OVERVIEW.md` |
| updated | `docs/architecture/COMPONENTS.md` |
| updated | `docs/architecture/DATA_FLOW.md` |
| updated | `docs/architecture/DEPENDENCY_RULES.md` |
| updated | `docs/architecture/DEPLOYMENT.md` |
| updated | `docs/architecture/OVERVIEW.md` |
| updated | `docs/architecture/foundation.md` |
| updated | `docs/decisions/0001-clean-architecture.md` |
| updated | `docs/decisions/0002-money-representation.md` |
| updated | `docs/decisions/0003-immutable-market-snapshots.md` |
| updated | `docs/decisions/0004-random-sequence-reproducibility.md` |
| updated | `docs/decisions/0005-correlation-validation.md` |
| updated | `docs/decisions/0006-persistence-boundaries.md` |
| updated | `docs/decisions/0007-deterministic-curves-and-pricing.md` |
| updated | `docs/decisions/0008-stochastic-models-and-discretization.md` |
| updated | `docs/decisions/0009-bounded-calibration-and-uncertainty.md` |
| updated | `docs/decisions/0010-independent-sampling-units.md` |
| updated | `docs/decisions/0011-batched-paths-and-gaussian-covariance.md` |
| updated | `docs/decisions/0012-legal-portfolio-snapshots.md` |
| updated | `docs/decisions/0013-collateral-ledger-and-margin-policy.md` |
| updated | `docs/decisions/0014-conditional-market-paths.md` |
| updated | `docs/decisions/0015-credit-default-dependence.md` |
| updated | `docs/decisions/0016-exposure-statistics-and-cash-policy.md` |
| updated | `docs/decisions/0017-unilateral-credit-adjustments.md` |
| updated | `docs/decisions/0018-additive-funding-and-external-margin.md` |
| updated | `docs/decisions/0019-xva-common-stream-risk-attribution.md` |
| updated | `docs/decisions/0020-restricted-standardized-ccr.md` |
| updated | `docs/decisions/0021-legal-unit-imm-challenger.md` |
| updated | `docs/decisions/0022-ccr-capital-comparison.md` |
| updated | `docs/decisions/0023-validation-comparability.md` |
| updated | `docs/decisions/0024-validation-inference.md` |
| updated | `docs/decisions/0025-sourced-stress-scenarios.md` |
| updated | `docs/decisions/0026-controlled-quantitative-mutations.md` |
| updated | `docs/decisions/0027-bounded-adversarial-search.md` |
| updated | `docs/decisions/0028-material-change-forensics.md` |
| updated | `docs/decisions/README.md` |
| updated | `docs/methodology/INDEX.md` |
| updated | `docs/methodology/primitives.md` |
| updated | `docs/operations/CONFIGURATION.md` |
| updated | `docs/operations/DATABASE.md` |
| updated | `docs/operations/DOCKER.md` |
| updated | `docs/operations/LOCAL_SETUP.md` |
| updated | `docs/operations/OBSERVABILITY.md` |
| updated | `docs/operations/RELEASE.md` |
| updated | `docs/operations/TROUBLESHOOTING.md` |
| updated | `docs/testing/STRATEGY.md` |
| updated | `docs/tutorials/09-FIRST-ADVERSARIAL-RUN.md` |
| updated | `docs/validation/OVERVIEW.md` |
| updated | `docs/workflows/VALIDATION_WORKFLOW.md` |
| updated | `pyproject.toml` |
| updated | `src/parallax_risk/__init__.py` |
| updated | `src/parallax_risk/api/app.py` |
| updated | `src/parallax_risk/api/schemas.py` |
| updated | `src/parallax_risk/cli/main.py` |
| updated | `tests/api/test_operations.py` |
| updated | `tests/integration/test_database_cli.py` |
