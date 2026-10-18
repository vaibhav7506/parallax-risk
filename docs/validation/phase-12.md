# Parallax Risk — Phase 12 implementation and verification

Status: COMPLETE; release 0.12.0. Client date: 2026-10-02.
Exactly Phase 12 is authorized. No Phase 13 is planned or scaffolded.

Implemented versioned authenticated financial/lab/governance/report workflows, strict
nominal wire schemas, immutable PostgreSQL inputs/durable jobs/claim CAS, success-linked
lineage, local asynchronous workers, production CLI, explicit resource lifetimes and
capacity controls. Numerical formulas retain existing research assumptions; cumulative
collateral history validation preserves exact Money ordering and all historical checks.

## Actual verification results

- Initial API/architecture checks: 8 passed with the existing Starlette/httpx warning.
- Real engine checks executed all 16 operations. Initial sample quarterly CSA grid was
  rejected; fixed the synthetic example to a complete daily grid without weakening guards.
  Exact credit horizon checks then rejected the shorter sample until its declared hazard
  horizons were explicitly supplied consistently.
- New wire tests caught integer-zero/binary64 example hash differences; corrected the
  synthetic model inputs. Nominal schema generation needed the explicitly allowed concrete
  ReducedFormSpread protocol mapping. Runtime CLI generic argparse annotation needed
  postponed evaluation; strict mypy alone did not catch this runtime import defect.
- Live focused Docker/PostgreSQL run after fixes: 58 passed, existing warning, 71.90s.
  It exercised fresh/repeated/downgrade/reupgrade migration, immutable SQL evidence,
  concurrent idempotency/admission/exclusive claims, CAS completion with committed lineage,
  sanitized rollback, owner/role guards and all actual demo computations/replay/reports.
- API guard tests: 26 passed; CLI adapter/protocol tests: 32 passed; worker fault-state and
  explicit-budget tests: 18 passed. These are focused results, not a full-suite claim.
- Strict mypy: 158 source files passed before final verification. Ruff passed after formatting.
- Isolated pip-audit 2.10.1 checked exact runtime/development pins with strict collection
  using the PyPI advisory service: no known vulnerabilities found. This is point-in-time
  advisory coverage, not a security certification; version-only locks have no artifact hashes.
- Actual measured profiling/memory/vectorization/large-book/parallel evidence is described
  in [benchmark method/results](SERVICE_BENCHMARKS.md). No claimed process-pool speedup.
- First full image startup/migration/check-db succeeded; HTTP computations/replay/reports
  completed, but report downloads hit the unchanged default rate quota. The demo now paces
  HTTP calls; preserved the failure logs and removed only owned verification resources.
  All 35 unrelated container identities remained in the before/after inventory.
- Second full attempt: actual HTTP/CLI demo succeeded; Windows had 1604 passed / one
  failure because an operational CLI test expected 0.11.0. Updated that assertion to
  the package version without altering the version command. Preserved attempt logs.
- CLI review additionally fixed invalid-port/bracket URLs, hidden credential-file bytes,
  invalid idempotency headers and non-UTF-8 response errors. Focused checks: 48 passed,
  one DB test skipped with no live success inferred for that focused invocation.
- Final Windows suite with actual PostgreSQL 17.11: **1610 passed, one existing
  Starlette/httpx deprecation warning, 682.16s**, no skips. Statement coverage
  9983/10164 (98.2192%); branches 2620/2728 (96.0411%); combined 97.7583%, above 95%.
- Native isolated wheel/sdist build succeeded with declared build backend hatchling
  1.32.4. Clean Windows pinned-runtime environment installed the wheel; pip check,
  CLI version/help and API/OpenAPI factory import succeeded (47 route paths). An
  initial --no-isolation attempt failed because hatchling was not in the runtime/dev
  environment; using the declared isolated build resolved it.
- All 159 production files match frozen source, installed Docker image, wheel and
  sdist. The sdist contains no ignored artifacts/raw credentials. The 18 historical
  phase/maintenance reports and docs/adr files are byte-identical to Phase 11 baseline.
- Three code hooks passed with an explicit project-interpreter temporary configuration.
  Default hook resolution had selected base Python without Ruff/mypy; failure log is
  retained. Separate full Ruff, 390-file format check and strict mypy (158 files) passed.
- Credential provisioning created a fresh opaque key plus digest-only configuration;
  strict client/settings validation passed, and its disposable raw key was removed.
- Dependency audit covered **99 unique pinned distributions, zero known advisory
  vulnerabilities**. No dependency pins or coverage exclusions changed in this phase.
- Installed-wheel Linux Python 3.12.14 suite against actual PostgreSQL 17.11:
  **1610 passed, the same existing warning, 1068.87s**, no skips. All statement/branch
  coverage totals match Windows exactly: combined **97.75829972075707%**. Linux
  tests import the installed wheel from site-packages, not a PYTHONPATH source override.
- Real HTTP demo completed all 16 operations, actual calibrated-parameter deployment,
  retained-input XVA replay and all seven HTML/JSON report types. Production XVA CLI
  replay and governance query succeeded. All 20 service command help paths work in
  the clean installed-wheel environment.
- Release image: `sha256:f38174a637927540d36f551a9035d7558512c2d1c5b8b37f419f6db2ab111e04`;
  runtime UID **10001**. Production credentials, explicit migration and schema/worker
  readiness succeeded before API demonstration. The same digest is retained after tests.
- Finally cleanup removed the two owned API/PostgreSQL verification containers,
  `parallax-risk-phase12-verification_default` network and disposable postgres_data
  volume. The labelled Linux test container used --rm and removed its temporary files
  automatically. All **35 unrelated container identities/names/projects** match before
  and after exactly. No normal persistent project database, useful image or shared
  layer/build cache was removed. Preview and apply modes were actually exercised.
- Final packages refresh documentation after these code checks; all 159 production
  bytes remain identical to the frozen tested image. Final artifact hashes/manifest and
  documentation checks are saved with the release evidence. No hosted CI result,
  external deployment or fabricated source commit is claimed.

## Scope and review

[Service contracts](../methodology/SERVICE.md), [operations](../operations/SERVICE.md),
[API](../api/ENDPOINTS.md), [limitations](../LIMITATIONS.md), [final audit](FINAL_AUDIT.md).
The manifest and actual release results below record the completed final phase. No Phase 13 work is authorized.


## Architecture and workflow changes

API/CLI compose lifecycle-owned SQLAlchemy/probe/worker resources. Application selects
exact wire root types and rejects invalid economic inputs before queuing. Infrastructure
implements digest authentication, bounded same-origin HTTP, immutable PostgreSQL
objects/jobs, exclusive SKIP LOCKED claims and completion CAS. Quantitative logic stays
in the existing domain/application engines. Versioned jobs retain complete requests and
results; successful completion requires committed registered-model lineage. Governance
actors/decision authority are tied to authenticated explicit roles.

Service admission bounds path/trade/step/driver/case/search/resampling/calibration work,
including cumulative collateral-history cost, plus request/output bytes and pending jobs.
Those are validated estimates, not hard CPU-time or full-RSS guarantees. Local worker
threads halt on uncertain infrastructure errors; no automatic retry or distributed lease
recovery is implemented. Retained reports derive compatible owned successful results.

## Assumptions, limitations and optional choices

All samples are synthetic. The end-to-end example uses daily 30-day exposure and
consistent declared hazard horizons; capital uses a separate full-year grid and explicit
business-day margin assumptions. Actual Vasicek calibration is fitted before simulation
and linked to job lineage; shared fitted rate parameters across two synthetic currencies
are a demonstration assumption. Calibration deployment linking currently accepts only
VasicekBondProblem. Other supported calibrations can execute as their own jobs.

Small demonstration path counts are functional replay evidence, not tail accuracy.
Weak mutation validation deliberately misses 14 of 15 probes; this remains an open high
finding with a conditional research decision. Adversarial evaluations are real and finite,
while their deliberately small search budget retains nonconvergence status. Numerical
model cards preserve Gaussian/Heston/credit/XVA/CSA/restricted-CCR limitations.

Lineage and job completion are separate transactions. A failed final persistence step
can leave committed lineage and a running uncertain job; inspect before explicit owned
abandonment/replay. Static keys, shared research-governance inventory and owner-scoped
objects are not enterprise identity/tenancy, signed decisions, HA or certification.
No service retention-purge or monitoring scheduler was added. Optional PDF, Redis,
separate workers, production processes/distribution, Numba/JAX/GPU, QuantLib/ORE, Latin
hypercube and Shapley adapters were not selected; no empty future pages were created.
Hosted Actions and Python 3.14 were not executed.

## Documentation and decision review

Created service methodology/operations, consolidated implemented model cards, actual
benchmark method/results, final master audit, this report, four new ADRs and a synthetic
service-fixture guide. Reviewed/updated affected root guidance, architecture, API/error/
example guides, code navigation/domain relationships/glossary, reproducibility, financial
limits, test strategy, setup/database/configuration/observability/release/cleanup and
validation/governance learning paths. Earlier phase reports remain unchanged.

Reviewed **all 36 canonical ADRs** and appended Phase 12 rows. Added **0033–0036**;
extended 0001, 0013, 0029, 0030 and 0032: **9 material decision changes**. ADR 0006
remains superseded by 0029; totals are 35 accepted / one superseded. No ID reused.
Added nominal wire schema, idempotency key, claim token, uncertain running job, principal,
keyset page and synthetic report flag to the glossary.

Corrected stale current-guide claims about future financial APIs, no persisted input/
result schema, unauthenticated service authority, connectivity-only readiness and old
release helpers. Historical scope paragraphs explicitly retain their introduction phase.
The final audit records all **702 bullet/numbered requirements** and **52 narrative
objectives/controls**, with concrete evidence and optional/research qualifiers.

## Commands and retained evidence

Current commands exercised: Ruff/format/strict mypy, explicit project code hooks,
pytest/coverage JSON with live PostgreSQL, zero/repeat/down/up migration, Compose
configuration/build/start/check-db, health/ready/version, all-16 HTTP demo, actual XVA
CLI retained-input replay, governance query, credential provisioning, package build/
clean runtime install/pip check/help/OpenAPI, pinned dependency audit and measured
benchmark scripts. Documentation checker verifies links, source references, reachability
and ADR/phase bookkeeping; external URL availability is not claimed by that checker.

Ignored artifacts/local/phase12 retains full command/failed-attempt logs, actual coverage,
HTTP/CLI replay summary, 14 HTML/JSON report files, 16 retained JobInput files, benchmark
JSON/profile, audit JSON, source/image/package hashes and before/after Docker inventory.
Useful wheel/sdist, locked runtime/development requirements, release/rollback images,
shared Docker layers/cache, normal persistent data and unrelated resources are retained.
Raw disposable verification/provisioning API keys are removed after use.

## Phase file manifest

Relative to the frozen 378-file Phase 11 baseline; generated artifacts/environments and
.git are excluded. This manifest records actual repository additions/modifications, not
commits (the workspace has no source commit to claim).

**44 created, 87 updated, 0 removed; 422 current repository files.**
Documentation: 11 created and 70 updated, including every canonical ADR.

| Change | Repository file |
|---|---|
| Created | [data/sample/service/README.md](../../data/sample/service/README.md) |
| Created | [data/sample/service/calibration.json](../../data/sample/service/calibration.json) |
| Created | [data/sample/service/market.json](../../data/sample/service/market.json) |
| Created | [data/sample/service/portfolio.json](../../data/sample/service/portfolio.json) |
| Created | [data/sample/service/pricing-context.json](../../data/sample/service/pricing-context.json) |
| Created | [docs/decisions/0033-nominal-service-wire.md](../decisions/0033-nominal-service-wire.md) |
| Created | [docs/decisions/0034-durable-service-jobs.md](../decisions/0034-durable-service-jobs.md) |
| Created | [docs/decisions/0035-service-authentication-and-limits.md](../decisions/0035-service-authentication-and-limits.md) |
| Created | [docs/decisions/0036-cumulative-collateral-history.md](../decisions/0036-cumulative-collateral-history.md) |
| Created | [docs/methodology/SERVICE.md](../methodology/SERVICE.md) |
| Created | [docs/models/INDEX.md](../models/INDEX.md) |
| Created | [docs/operations/SERVICE.md](../operations/SERVICE.md) |
| Created | [docs/validation/FINAL_AUDIT.md](FINAL_AUDIT.md) |
| Created | [docs/validation/SERVICE_BENCHMARKS.md](SERVICE_BENCHMARKS.md) |
| Created | [docs/validation/phase-12.md](phase-12.md) |
| Created | [scripts/benchmark_service.py](../../scripts/benchmark_service.py) |
| Created | [scripts/create_service_credentials.py](../../scripts/create_service_credentials.py) |
| Created | [scripts/demo_service.py](../../scripts/demo_service.py) |
| Created | [scripts/verify_phase12.ps1](../../scripts/verify_phase12.ps1) |
| Created | [src/parallax_risk/api/guard.py](../../src/parallax_risk/api/guard.py) |
| Created | [src/parallax_risk/api/routes.py](../../src/parallax_risk/api/routes.py) |
| Created | [src/parallax_risk/api/service_schemas.py](../../src/parallax_risk/api/service_schemas.py) |
| Created | [src/parallax_risk/application/access.py](../../src/parallax_risk/application/access.py) |
| Created | [src/parallax_risk/application/jobs.py](../../src/parallax_risk/application/jobs.py) |
| Created | [src/parallax_risk/application/service.py](../../src/parallax_risk/application/service.py) |
| Created | [src/parallax_risk/application/service_config.py](../../src/parallax_risk/application/service_config.py) |
| Created | [src/parallax_risk/application/service_demo.py](../../src/parallax_risk/application/service_demo.py) |
| Created | [src/parallax_risk/application/service_examples.py](../../src/parallax_risk/application/service_examples.py) |
| Created | [src/parallax_risk/application/wire.py](../../src/parallax_risk/application/wire.py) |
| Created | [src/parallax_risk/application/wire_schema.py](../../src/parallax_risk/application/wire_schema.py) |
| Created | [src/parallax_risk/application/workflows.py](../../src/parallax_risk/application/workflows.py) |
| Created | [src/parallax_risk/cli/service.py](../../src/parallax_risk/cli/service.py) |
| Created | [src/parallax_risk/infrastructure/authentication.py](../../src/parallax_risk/infrastructure/authentication.py) |
| Created | [src/parallax_risk/infrastructure/http_client.py](../../src/parallax_risk/infrastructure/http_client.py) |
| Created | [src/parallax_risk/infrastructure/persistence/migrations/versions/phase12_service.py](../../src/parallax_risk/infrastructure/persistence/migrations/versions/phase12_service.py) |
| Created | [src/parallax_risk/infrastructure/persistence/service.py](../../src/parallax_risk/infrastructure/persistence/service.py) |
| Created | [src/parallax_risk/infrastructure/service_composition.py](../../src/parallax_risk/infrastructure/service_composition.py) |
| Created | [src/parallax_risk/infrastructure/worker.py](../../src/parallax_risk/infrastructure/worker.py) |
| Created | [tests/api/test_service_security.py](../../tests/api/test_service_security.py) |
| Created | [tests/integration/test_service_postgres.py](../../tests/integration/test_service_postgres.py) |
| Created | [tests/unit/test_collateral_history_optimization.py](../../tests/unit/test_collateral_history_optimization.py) |
| Created | [tests/unit/test_service_cli.py](../../tests/unit/test_service_cli.py) |
| Created | [tests/unit/test_service_wire.py](../../tests/unit/test_service_wire.py) |
| Created | [tests/unit/test_service_worker.py](../../tests/unit/test_service_worker.py) |
| Updated | [.env.example](../../.env.example) |
| Updated | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) |
| Updated | [AGENTS.md](../../AGENTS.md) |
| Updated | [CHANGELOG.md](../../CHANGELOG.md) |
| Updated | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
| Updated | [DEVELOPMENT.md](../../DEVELOPMENT.md) |
| Updated | [README.md](../../README.md) |
| Updated | [ROADMAP.md](../../ROADMAP.md) |
| Updated | [SECURITY.md](../../SECURITY.md) |
| Updated | [docker-compose.yml](../../docker-compose.yml) |
| Updated | [docs/CODEBASE_GUIDE.md](../CODEBASE_GUIDE.md) |
| Updated | [docs/DOMAIN_MODEL.md](../DOMAIN_MODEL.md) |
| Updated | [docs/GLOSSARY.md](../GLOSSARY.md) |
| Updated | [docs/INDEX.md](../INDEX.md) |
| Updated | [docs/LIMITATIONS.md](../LIMITATIONS.md) |
| Updated | [docs/REPRODUCIBILITY.md](../REPRODUCIBILITY.md) |
| Updated | [docs/WORKFLOW.md](../WORKFLOW.md) |
| Updated | [docs/api/ENDPOINTS.md](../api/ENDPOINTS.md) |
| Updated | [docs/api/ERRORS.md](../api/ERRORS.md) |
| Updated | [docs/api/EXAMPLES.md](../api/EXAMPLES.md) |
| Updated | [docs/api/OVERVIEW.md](../api/OVERVIEW.md) |
| Updated | [docs/architecture/COMPONENTS.md](../architecture/COMPONENTS.md) |
| Updated | [docs/architecture/DATA_FLOW.md](../architecture/DATA_FLOW.md) |
| Updated | [docs/architecture/DEPENDENCY_RULES.md](../architecture/DEPENDENCY_RULES.md) |
| Updated | [docs/architecture/DEPLOYMENT.md](../architecture/DEPLOYMENT.md) |
| Updated | [docs/architecture/OVERVIEW.md](../architecture/OVERVIEW.md) |
| Updated | [docs/architecture/foundation.md](../architecture/foundation.md) |
| Updated | [docs/decisions/0001-clean-architecture.md](../decisions/0001-clean-architecture.md) |
| Updated | [docs/decisions/0002-money-representation.md](../decisions/0002-money-representation.md) |
| Updated | [docs/decisions/0003-immutable-market-snapshots.md](../decisions/0003-immutable-market-snapshots.md) |
| Updated | [docs/decisions/0004-random-sequence-reproducibility.md](../decisions/0004-random-sequence-reproducibility.md) |
| Updated | [docs/decisions/0005-correlation-validation.md](../decisions/0005-correlation-validation.md) |
| Updated | [docs/decisions/0006-persistence-boundaries.md](../decisions/0006-persistence-boundaries.md) |
| Updated | [docs/decisions/0007-deterministic-curves-and-pricing.md](../decisions/0007-deterministic-curves-and-pricing.md) |
| Updated | [docs/decisions/0008-stochastic-models-and-discretization.md](../decisions/0008-stochastic-models-and-discretization.md) |
| Updated | [docs/decisions/0009-bounded-calibration-and-uncertainty.md](../decisions/0009-bounded-calibration-and-uncertainty.md) |
| Updated | [docs/decisions/0010-independent-sampling-units.md](../decisions/0010-independent-sampling-units.md) |
| Updated | [docs/decisions/0011-batched-paths-and-gaussian-covariance.md](../decisions/0011-batched-paths-and-gaussian-covariance.md) |
| Updated | [docs/decisions/0012-legal-portfolio-snapshots.md](../decisions/0012-legal-portfolio-snapshots.md) |
| Updated | [docs/decisions/0013-collateral-ledger-and-margin-policy.md](../decisions/0013-collateral-ledger-and-margin-policy.md) |
| Updated | [docs/decisions/0014-conditional-market-paths.md](../decisions/0014-conditional-market-paths.md) |
| Updated | [docs/decisions/0015-credit-default-dependence.md](../decisions/0015-credit-default-dependence.md) |
| Updated | [docs/decisions/0016-exposure-statistics-and-cash-policy.md](../decisions/0016-exposure-statistics-and-cash-policy.md) |
| Updated | [docs/decisions/0017-unilateral-credit-adjustments.md](../decisions/0017-unilateral-credit-adjustments.md) |
| Updated | [docs/decisions/0018-additive-funding-and-external-margin.md](../decisions/0018-additive-funding-and-external-margin.md) |
| Updated | [docs/decisions/0019-xva-common-stream-risk-attribution.md](../decisions/0019-xva-common-stream-risk-attribution.md) |
| Updated | [docs/decisions/0020-restricted-standardized-ccr.md](../decisions/0020-restricted-standardized-ccr.md) |
| Updated | [docs/decisions/0021-legal-unit-imm-challenger.md](../decisions/0021-legal-unit-imm-challenger.md) |
| Updated | [docs/decisions/0022-ccr-capital-comparison.md](../decisions/0022-ccr-capital-comparison.md) |
| Updated | [docs/decisions/0023-validation-comparability.md](../decisions/0023-validation-comparability.md) |
| Updated | [docs/decisions/0024-validation-inference.md](../decisions/0024-validation-inference.md) |
| Updated | [docs/decisions/0025-sourced-stress-scenarios.md](../decisions/0025-sourced-stress-scenarios.md) |
| Updated | [docs/decisions/0026-controlled-quantitative-mutations.md](../decisions/0026-controlled-quantitative-mutations.md) |
| Updated | [docs/decisions/0027-bounded-adversarial-search.md](../decisions/0027-bounded-adversarial-search.md) |
| Updated | [docs/decisions/0028-material-change-forensics.md](../decisions/0028-material-change-forensics.md) |
| Updated | [docs/decisions/0029-governance-persistence.md](../decisions/0029-governance-persistence.md) |
| Updated | [docs/decisions/0030-governed-risk-lineage.md](../decisions/0030-governed-risk-lineage.md) |
| Updated | [docs/decisions/0031-monitoring-alert-transitions.md](../decisions/0031-monitoring-alert-transitions.md) |
| Updated | [docs/decisions/0032-evidence-report-rendering.md](../decisions/0032-evidence-report-rendering.md) |
| Updated | [docs/decisions/README.md](../decisions/README.md) |
| Updated | [docs/methodology/INDEX.md](../methodology/INDEX.md) |
| Updated | [docs/operations/CONFIGURATION.md](../operations/CONFIGURATION.md) |
| Updated | [docs/operations/DATABASE.md](../operations/DATABASE.md) |
| Updated | [docs/operations/DOCKER.md](../operations/DOCKER.md) |
| Updated | [docs/operations/LOCAL_SETUP.md](../operations/LOCAL_SETUP.md) |
| Updated | [docs/operations/OBSERVABILITY.md](../operations/OBSERVABILITY.md) |
| Updated | [docs/operations/RELEASE.md](../operations/RELEASE.md) |
| Updated | [docs/operations/TROUBLESHOOTING.md](../operations/TROUBLESHOOTING.md) |
| Updated | [docs/testing/STRATEGY.md](../testing/STRATEGY.md) |
| Updated | [docs/tutorials/08-FIRST-VALIDATION-RUN.md](../tutorials/08-FIRST-VALIDATION-RUN.md) |
| Updated | [docs/validation/OVERVIEW.md](OVERVIEW.md) |
| Updated | [docs/workflows/GOVERNANCE_WORKFLOW.md](../workflows/GOVERNANCE_WORKFLOW.md) |
| Updated | [docs/workflows/VALIDATION_WORKFLOW.md](../workflows/VALIDATION_WORKFLOW.md) |
| Updated | [pyproject.toml](../../pyproject.toml) |
| Updated | [scripts/migrate_governance.py](../../scripts/migrate_governance.py) |
| Updated | [src/parallax_risk/__init__.py](../../src/parallax_risk/__init__.py) |
| Updated | [src/parallax_risk/api/app.py](../../src/parallax_risk/api/app.py) |
| Updated | [src/parallax_risk/api/schemas.py](../../src/parallax_risk/api/schemas.py) |
| Updated | [src/parallax_risk/application/config.py](../../src/parallax_risk/application/config.py) |
| Updated | [src/parallax_risk/application/governance.py](../../src/parallax_risk/application/governance.py) |
| Updated | [src/parallax_risk/cli/main.py](../../src/parallax_risk/cli/main.py) |
| Updated | [src/parallax_risk/domain/portfolio/collateral.py](../../src/parallax_risk/domain/portfolio/collateral.py) |
| Updated | [src/parallax_risk/infrastructure/persistence/governance.py](../../src/parallax_risk/infrastructure/persistence/governance.py) |
| Updated | [src/parallax_risk/infrastructure/persistence/migrate.py](../../src/parallax_risk/infrastructure/persistence/migrate.py) |
| Updated | [tests/api/test_operations.py](../../tests/api/test_operations.py) |
| Updated | [tests/integration/test_database_cli.py](../../tests/integration/test_database_cli.py) |
| Updated | [tests/integration/test_governance_postgres.py](../../tests/integration/test_governance_postgres.py) |
