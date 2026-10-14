# Parallax Risk Phase 9 implementation and verification

**Phase 9 complete; release 0.9.0; 2026-10-01.**
Phase 10 mutation/adversarial lab is NOT IMPLEMENTED. Both corrected full suites passed; actual results and the preserved first-attempt
failure are recorded below.

## Implemented scope

Injected production/challenger protocols compare identical immutable cases and
explicit metric/unit/component schemas. Actual production credit quadrature is
challenged by analytical constant-EE and independent adaptive-integral targets.
Model differences retain components and unexplained residuals. Automatic independent
CVA invariants and five-valuation local finite differences produce checks/findings.
Actual exposure/XVA adapters support independent CVA/EPE path observations, path-count
and time-step studies, approximate t intervals, stability/precision thresholds.
Owned independent-unit bootstrap, actual parameter ensembles and available calibration
covariance propagation produce distinctly labelled risk bands. A flat-hazard probability
objective is actually calibrated by the existing solver. Actual hypothetical/combined
stress revaluations and caller-sourced dated observation adapters retain provenance.
Immutable Finding retains severity, evidence, metric, reproduction, version and status.

[Methodology](../methodology/MODEL_VALIDATION.md), [uncertainty](../methodology/MODEL_UNCERTAINTY.md),
[stress](../methodology/STRESS_SCENARIOS.md), [workflow](../workflows/VALIDATION_WORKFLOW.md).

## Assumptions and limitations

Signed CVA costs are negative reporting-currency units; hazard/rate are annual decimal,
discount continuously compounded, times ACT/365F from zero. Benchmarks assume independent
credit and deterministic discount with linear exposure. Fixed-cash collateral checks
are idealizations, not universal dynamic CSA monotonicity. Finite ladders do not bound
bias; grid normal mappings differ and are not nested Brownian coupling. IID/pair/scramble
units are explicit; single Sobol point inference and dependent path CVA reject here.
Bootstrap is conditional approximate percentile coverage; ensemble ranges have no
probability law; local calibration normal bands do not cover full model uncertainty.
Historical provenance is caller-supplied, not a feed or authenticated history. All demo
and dated adapter test data are labelled synthetic. Findings are not approvals.
No new dependency, migration, persistent governance, financial API, monitoring,
adversarial search, controlled mutation or performance/accuracy claim is added.

## Decisions and documentation

All 22 earlier canonical ADRs receive Phase 9 reviews; 0023 comparability/findings,
0024 inference/uncertainty and 0025 sourced stress are introduced with preserved prior
not-implemented history. 0001 is extended with inward lab boundaries; 0009 refines exact-symmetric SVD covariance construction. No ADR is replaced.
Historical docs/adr records and Phase 1–8/maintenance evidence remain byte-preserved.
New terms: model output schema, unexplained model difference, validation Finding,
finite-ladder stability, percentile bootstrap, parameter ensemble, delta-method band,
historical shock replay and ordered combined stress. Detailed Phase 10–12 pages are deferred.

## Verification, manifest and Docker

The actual environments/results, commands, manifest, retained release artifacts
and project-scoped cleanup evidence are recorded below.
The baseline is the retained 0.8.0 source archive, with 302 SHA-256 file entries in
artifacts/local/phase9/baseline-0.8.0.json. This workspace has no source commit.

## First verification attempt and correction

Windows first full run: 1208 passed, one warning, 192.90 s, 99.27% branch-inclusive
coverage. Linux first full run: 1 failed, 1207 passed, one warning, 205.49 s, same
coverage. Actual fitted covariance differed by roughly one ulp between transposed
entries, so the new exact-symmetry boundary rejected propagation. The estimator now
constructs each weighted SVD Gram entry once and shares it across symmetric positions;
caller matrix rejection/PSD checks remain intact. An independent 2x2 inverse target
checks the estimator and exact symmetry. Both full suites were rerun successfully. All first
attempt logs/cleanup/results remain under artifacts/local/phase9/first-attempt.
The initial demo also required explicit CalibrationSolver injection from the script;
architecture checks passed after that correction and the verification image was refreshed
before the installed-wheel Linux run. No historical report/test outcome was overwritten.

## Final full verification

The corrected source passed 1209 tests on Windows Python 3.13.2 with live isolated
PostgreSQL 17, one existing Starlette/httpx deprecation warning, 185.38 s. Full
branch-inclusive coverage is 99.25%: 6873 statements, 1812 branches, 34 missing
statements, 31 missing/partial branches. The ten new production modules collectively
have 97.72% branch-inclusive coverage; contracts/uncertainty/invariants/demo composition
are 100%. The refined existing calibration adapter is 95.04%. No coverage exemption,
skipped database verification, tolerance weakening or warning suppression was added.

Ruff check and format check passed for the full repository (302 formatted files),
strict mypy passed for 114 source files, and the existing pre-commit hooks passed
with an ignored temporary configuration explicitly selecting the project interpreter.
The canonical hook configuration is unchanged. Documentation checks passed with
122 Markdown files, 25 canonical ADRs and 1045 concrete path references. External URLs
are syntax checked there, not claimed as fetched by the checker.

Commands verified include the actual focused pytest commands, full Windows/live-PG
suite through the helper, demo subprocess replay, module CLI version/help, project
Ruff/format/mypy, canonical hook entries with explicit local interpreter, docs checker,
editable install and isolated packaging. Docker/Compose configuration, liveness,
connected readiness, version 0.9.0/phase 9 and CLI check-db were executed. Final Linux verification, runtime UID and cleanup inventory passed as recorded below.
The final source/wheel refresh includes completion documentation and matches production source.

## Synthetic evidence interpretation

Two demo subprocesses produced identical 70,358-byte stdout with SHA-256
f50d0e8f475e450eff43e6eff32119a35e70743dd58b42ff601949462cc4fa89.
Its 12 checks retain five failures: production/analytical CVA discrepancy
0.00028472859872152867 USD exceeds 0.0001 USD, and four supplied path/grid stability
or precision bounds fail. The actual path ladder is 16/32/64 and the independent-unit
bootstrap retains 128 replicate statistics. These are synthetic numerical observations,
not market accuracy or model approval. Reused XVA inputs retain their explicit Phase 7
synthetic identifiers and mathematical model version; the lab release is 0.9.0.

## Documentation and current-scope corrections

Nine Markdown documents were created (three methodologies, workflow, tutorial, phase
report and three ADRs), 58 updated. Twenty-four repository files were created, 68
updated and none removed. All 25 ADRs have a Phase 9 history review; five material IDs
are 0001, 0009, 0023, 0024, 0025. Prior history and all 15 protected historical records
remain byte-preserved. Definitions, architecture, workflow, limits, reproducibility,
methodology, testing, operations, API metadata and active commands were reviewed.

Corrected stale active-scope statements that the lab/Finding were unimplemented,
glossary default-loss deferral, stale capital-model deferral and the planned-only
workflow diagram. Corrected demo
solver composition and covariance construction after actual verification evidence.
Dependency locks, existing notebooks, docs checker, cleanup script, domain financial
pricing/XVA formulas and database schema are unchanged. Calibration covariance now
uses the same estimator with exact symmetric numerical construction. Phase 10–12
detailed mutation/adversarial/governance/financial production pages remain deferred.

## File manifest against retained 0.8.0 source archive

| Change | Repository file |
|---|---|
| Created | `docs/decisions/0023-validation-comparability.md` |
| Created | `docs/decisions/0024-validation-inference.md` |
| Created | `docs/decisions/0025-sourced-stress-scenarios.md` |
| Created | `docs/methodology/MODEL_UNCERTAINTY.md` |
| Created | `docs/methodology/MODEL_VALIDATION.md` |
| Created | `docs/methodology/STRESS_SCENARIOS.md` |
| Created | `docs/tutorials/08-FIRST-VALIDATION-RUN.md` |
| Created | `docs/validation/phase-9.md` |
| Created | `docs/workflows/VALIDATION_WORKFLOW.md` |
| Created | `scripts/demo_validation.py` |
| Created | `scripts/verify_phase9.ps1` |
| Created | `src/parallax_risk/application/validation.py` |
| Created | `src/parallax_risk/application/validation_examples.py` |
| Created | `src/parallax_risk/application/validation_invariants.py` |
| Created | `src/parallax_risk/application/validation_models.py` |
| Created | `src/parallax_risk/application/validation_stress.py` |
| Created | `src/parallax_risk/domain/validation/__init__.py` |
| Created | `src/parallax_risk/domain/validation/benchmark.py` |
| Created | `src/parallax_risk/domain/validation/checks.py` |
| Created | `src/parallax_risk/domain/validation/contracts.py` |
| Created | `src/parallax_risk/domain/validation/uncertainty.py` |
| Created | `tests/integration/test_validation_workflow.py` |
| Created | `tests/quantitative/test_validation_lab.py` |
| Created | `tests/unit/test_validation_guards.py` |
| Updated | `AGENTS.md` |
| Updated | `CHANGELOG.md` |
| Updated | `CONTRIBUTING.md` |
| Updated | `DEVELOPMENT.md` |
| Updated | `Makefile` |
| Updated | `README.md` |
| Updated | `ROADMAP.md` |
| Updated | `docker-compose.yml` |
| Updated | `docs/CODEBASE_GUIDE.md` |
| Updated | `docs/DOMAIN_MODEL.md` |
| Updated | `docs/GLOSSARY.md` |
| Updated | `docs/INDEX.md` |
| Updated | `docs/LIMITATIONS.md` |
| Updated | `docs/REPRODUCIBILITY.md` |
| Updated | `docs/WORKFLOW.md` |
| Updated | `docs/api/ENDPOINTS.md` |
| Updated | `docs/api/OVERVIEW.md` |
| Updated | `docs/architecture/COMPONENTS.md` |
| Updated | `docs/architecture/DATA_FLOW.md` |
| Updated | `docs/architecture/DEPENDENCY_RULES.md` |
| Updated | `docs/architecture/DEPLOYMENT.md` |
| Updated | `docs/architecture/OVERVIEW.md` |
| Updated | `docs/architecture/foundation.md` |
| Updated | `docs/decisions/0001-clean-architecture.md` |
| Updated | `docs/decisions/0002-money-representation.md` |
| Updated | `docs/decisions/0003-immutable-market-snapshots.md` |
| Updated | `docs/decisions/0004-random-sequence-reproducibility.md` |
| Updated | `docs/decisions/0005-correlation-validation.md` |
| Updated | `docs/decisions/0006-persistence-boundaries.md` |
| Updated | `docs/decisions/0007-deterministic-curves-and-pricing.md` |
| Updated | `docs/decisions/0008-stochastic-models-and-discretization.md` |
| Updated | `docs/decisions/0009-bounded-calibration-and-uncertainty.md` |
| Updated | `docs/decisions/0010-independent-sampling-units.md` |
| Updated | `docs/decisions/0011-batched-paths-and-gaussian-covariance.md` |
| Updated | `docs/decisions/0012-legal-portfolio-snapshots.md` |
| Updated | `docs/decisions/0013-collateral-ledger-and-margin-policy.md` |
| Updated | `docs/decisions/0014-conditional-market-paths.md` |
| Updated | `docs/decisions/0015-credit-default-dependence.md` |
| Updated | `docs/decisions/0016-exposure-statistics-and-cash-policy.md` |
| Updated | `docs/decisions/0017-unilateral-credit-adjustments.md` |
| Updated | `docs/decisions/0018-additive-funding-and-external-margin.md` |
| Updated | `docs/decisions/0019-xva-common-stream-risk-attribution.md` |
| Updated | `docs/decisions/0020-restricted-standardized-ccr.md` |
| Updated | `docs/decisions/0021-legal-unit-imm-challenger.md` |
| Updated | `docs/decisions/0022-ccr-capital-comparison.md` |
| Updated | `docs/decisions/README.md` |
| Updated | `docs/methodology/CALIBRATION.md` |
| Updated | `docs/methodology/INDEX.md` |
| Updated | `docs/methodology/MONTE_CARLO_STATISTICS.md` |
| Updated | `docs/operations/CONFIGURATION.md` |
| Updated | `docs/operations/DATABASE.md` |
| Updated | `docs/operations/DOCKER.md` |
| Updated | `docs/operations/LOCAL_SETUP.md` |
| Updated | `docs/operations/OBSERVABILITY.md` |
| Updated | `docs/operations/RELEASE.md` |
| Updated | `docs/operations/TROUBLESHOOTING.md` |
| Updated | `docs/testing/STRATEGY.md` |
| Updated | `docs/validation/BENCHMARKING.md` |
| Updated | `docs/validation/OVERVIEW.md` |
| Updated | `docs/validation/SENSITIVITY.md` |
| Updated | `pyproject.toml` |
| Updated | `src/parallax_risk/__init__.py` |
| Updated | `src/parallax_risk/api/schemas.py` |
| Updated | `src/parallax_risk/cli/main.py` |
| Updated | `src/parallax_risk/infrastructure/calibration/scipy_solver.py` |
| Updated | `tests/api/test_operations.py` |
| Updated | `tests/integration/test_database_cli.py` |
| Updated | `tests/quantitative/test_calibration.py` |

No repository files were removed. Before/after SHA-256 entries and final source/wheel
identities are retained under artifacts/local/phase9; archive hashes are not embedded
in their own packaged report. The final source archive refresh follows completion
documentation and is byte-checked against the workspace.

## Final Linux/runtime/cleanup and retention

The corrected installed-wheel Linux Python 3.12.14 suite passed **1209 tests**, one
existing Starlette/httpx warning, **188.12 s**, with live isolated PostgreSQL 17 and
**99.25% branch-inclusive coverage** (6873 statements, 1812 branches). Windows final
was **1209 passed**, one warning, **185.38 s**. The full suites include all applicable
quantitative, property, regression, integration and live database tests; PostgreSQL
was not skipped. The helper recorded production runtime UID **10001**, connected
CLI/database readiness and version **0.9.0/9**. Dependency locks were unchanged.

The tested retained image is
sha256:c707a74e5e14f476347b7d2a8ae5ff555a35cc8a2d66a03cf7f0b38a3de7cfef.
All **115 installed source/typed-marker files** byte-match the final workspace; the
saved read-only image hashes confirm the actual wheel, without PYTHONPATH override.
The image was built/tested before completion-documentation updates; its production
code matches final release source. The final wheel/source archive carries the completed
documentation and is independently checked. This workspace has no source commit;
archive SHA-256s and file hashes provide the actual completion evidence.

Both verification sessions invoked `scripts/cleanup_docker.ps1 -Phase 9 -Apply`
in finally after saving needed logs. Only owned disposable API/PostgreSQL containers,
parallax-risk-phase9-verification_default network and its postgres_data test volume
were removed. The explicitly labelled test containers used --rm; their temporary
writable files and development installs disappeared at exit. The earlier owned API
refresh replaced only its own verification container. No arbitrary in-container file
removal, global prune, force-image removal or operation on another project was used.
The final ownership preview finds zero phase-verification containers/networks/volumes.

All **35 unrelated container identities** match before/after in both sessions.
Normal persistent Compose parallax-risk database resources were outside cleanup scope.
Useful **0.1.0–0.9.0** release/rollback images, shared base layers/build cache, production
data and needed source/wheel/coverage/demo/replay/verification artifacts remain.
First-attempt logs/outcomes are retained separately. Image identities, preservation
records, final preview, source/wheel SHA-256s and before/after file hashes live under
artifacts/local/phase9. No new phase, governance approval or regulatory claim is implied.
