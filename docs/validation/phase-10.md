# Parallax Risk Phase 10 implementation and verification

**Phase 10 complete; release 0.10.0; 2026-10-01.**
Phase 11 governance remains NOT IMPLEMENTED and requires another `go`. Both full
release runs and ownership-scoped Docker cleanup passed as recorded below.

## Implemented scope and assumptions

Controlled isolated quantitative mutations cover all 15 requested classes. The
injected runner executes actual baseline/mutant validations, requires newly failed
baseline-passing checks and retains misses/category counts and reproduction. Built-in
synthetic operation probes exercise production CVA, LGD, day count, Cholesky, CSA
threshold, restricted CCR cash/MPOR, grid EAD, GBM diffusion, moments, interpolation
and default-mass operations. Direct FX is a declared conversion seam; dated look-ahead
and insufficient-path probes target observation selection and sampling diagnostics.
They are not whole-engine source mutations or a completed default-conditioned MPOR
model. No production fault toggle is introduced.

Bounded SciPy search retains every actual same-case model pair, explicit bounds,
linear constraints, owned stream, budget and optimizer status. Independent-credit
XVA CVA search additionally exercises all six requested factors with actual daily
CSA revaluation. Shared exposure simulation is outside the independent quadrature
challenge; no global maximum, selection correction or historical likelihood is claimed.

Materiality, changed input fingerprints, actual repeatability and ordered actual
counterfactual valuations produce seven possible-cause buckets and an explicit
unexplained residual. Overlapping labels/order dependence are not causal proof.
Complete input cases and model implementations must be retained alongside hashes.

No dependency, schema, database migration, governance persistence, financial HTTP
endpoint or Phase 11 implementation is added. Older financial model mathematics
versions remain unchanged; release metadata becomes 0.10.0 / phase 10.

## Verification record

The first constrained scalar optimizer test used a five-member population and found
.5149146070785743 instead of its known constrained maximum .6. It recorded **1 failed,
33 passed**. The mathematical target was retained; a larger declared population/budget
was used to verify the known optimum. This confirms that a stopping criterion does
not prove a global maximum. Subsequent focused checks passed. The final pre-install architecture check recorded
**1 failed, 130 passed** because the editable distribution still reported 0.9.0
after source metadata became 0.10.0. The existing isolated editable installation
was refreshed; no version assertion was weakened.

The first daily CSA test fixture used an incorrect MarginProfile keyword, then a
credit horizon inconsistent with its shortened grid. Production validation rejected
the latter explicitly. The fixture was corrected using actual field names and
matching credit horizon; no validation was bypassed. SciPy's wrapping of callback
ValueError was corrected to preserve the actual economic rejection.

Final actual results, full Windows/Linux/live-PostgreSQL runs, checks and resource
removal/retention are recorded below; source/wheel integrity is retained alongside
the file manifest after completion-document packaging.

## Documentation, decisions and file evidence

New methodology explains controlled mutations, bounded search and forensic evidence;
new workflow/tutorial explain actual entry points. Canonical ADRs 0026–0028 record
the new policies, with every earlier ADR reviewed for Phase 10 and history preserved.
New terminology: controlled mutant, baseline-qualified detection, equivalent mutant,
paired search evaluation, explicit plausibility restriction, possible-cause fingerprint,
repeatability finding and counterfactual residual.

Baseline SHA-256 inventory is retained under artifacts/local/phase10/baseline-0.9.0.json.
There is no source commit in this workspace. Final created/updated file manifest,
document counts, protected historical records and packaging hashes are retained
under artifacts/local/phase10 and are summarized below. Detailed governance,
monitoring/reporting and financial production API documents remain deferred to
Phases 11–12. The earlier 1209-test record is historical Phase 9 evidence only.

## Docker policy

`scripts/verify_phase10.ps1` uses only parallax-risk-phase10-verification, disposable
credentials and explicit project/purpose/workspace labels. Standalone test containers
use --rm; finally invokes `scripts/cleanup_docker.ps1 -Phase 10 -Apply`. Needed
results are saved before deleting temporary writable layers, network and test volume.
Useful release/rollback images, shared layers/cache, normal persistent Parallax Risk
database and unrelated/ambiguous resources are retained. No global prune or arbitrary
in-container file deletion is authorized.

## Phase file manifest

| Change | File |
|---|---|
| Created | `docs/decisions/0026-controlled-quantitative-mutations.md` |
| Created | `docs/decisions/0027-bounded-adversarial-search.md` |
| Created | `docs/decisions/0028-material-change-forensics.md` |
| Created | `docs/methodology/ADVERSARIAL_SEARCH.md` |
| Created | `docs/methodology/FAILURE_FORENSICS.md` |
| Created | `docs/methodology/QUANTITATIVE_MUTATION.md` |
| Created | `docs/tutorials/09-FIRST-ADVERSARIAL-RUN.md` |
| Created | `docs/validation/phase-10.md` |
| Created | `docs/workflows/ADVERSARIAL_WORKFLOW.md` |
| Created | `scripts/demo_adversarial.py` |
| Created | `scripts/verify_phase10.ps1` |
| Created | `src/parallax_risk/application/adversarial_examples.py` |
| Created | `src/parallax_risk/application/validation_forensics.py` |
| Created | `src/parallax_risk/application/validation_mutation.py` |
| Created | `src/parallax_risk/application/validation_probes.py` |
| Created | `src/parallax_risk/application/validation_search.py` |
| Created | `src/parallax_risk/application/validation_search_models.py` |
| Created | `src/parallax_risk/domain/validation/forensics.py` |
| Created | `src/parallax_risk/domain/validation/mutation.py` |
| Created | `src/parallax_risk/domain/validation/search.py` |
| Created | `src/parallax_risk/infrastructure/validation/__init__.py` |
| Created | `src/parallax_risk/infrastructure/validation/scipy_search.py` |
| Created | `tests/integration/test_adversarial_workflow.py` |
| Created | `tests/quantitative/test_adversarial_lab.py` |
| Created | `tests/unit/test_adversarial_guards.py` |
| Updated | `AGENTS.md` |
| Updated | `CHANGELOG.md` |
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
| Updated | `docs/decisions/0023-validation-comparability.md` |
| Updated | `docs/decisions/0024-validation-inference.md` |
| Updated | `docs/decisions/0025-sourced-stress-scenarios.md` |
| Updated | `docs/decisions/README.md` |
| Updated | `docs/methodology/CALIBRATION.md` |
| Updated | `docs/methodology/CORRELATION.md` |
| Updated | `docs/methodology/INDEX.md` |
| Updated | `docs/methodology/MODEL_UNCERTAINTY.md` |
| Updated | `docs/methodology/MODEL_VALIDATION.md` |
| Updated | `docs/methodology/STANDARDIZED_CCR.md` |
| Updated | `docs/methodology/STRESS_SCENARIOS.md` |
| Updated | `docs/methodology/XVA.md` |
| Updated | `docs/methodology/XVA_SENSITIVITIES.md` |
| Updated | `docs/operations/DATABASE.md` |
| Updated | `docs/operations/DOCKER.md` |
| Updated | `docs/operations/LOCAL_SETUP.md` |
| Updated | `docs/operations/OBSERVABILITY.md` |
| Updated | `docs/operations/RELEASE.md` |
| Updated | `docs/operations/TROUBLESHOOTING.md` |
| Updated | `docs/testing/STRATEGY.md` |
| Updated | `docs/tutorials/08-FIRST-VALIDATION-RUN.md` |
| Updated | `docs/validation/BENCHMARKING.md` |
| Updated | `docs/validation/OVERVIEW.md` |
| Updated | `docs/workflows/VALIDATION_WORKFLOW.md` |
| Updated | `pyproject.toml` |
| Updated | `src/parallax_risk/__init__.py` |
| Updated | `src/parallax_risk/api/schemas.py` |
| Updated | `src/parallax_risk/cli/main.py` |
| Updated | `tests/api/test_operations.py` |
| Updated | `tests/integration/test_database_cli.py` |

## Synthetic experiment evidence

The final canonical demo emitted **427,776 bytes**, SHA-256
`a317e25b8671465506bbe11b9ee4a981445fd68e9f3fbd5ecf838e770e2ddd76`, and an independent
same-runtime rerun was byte-identical. This does not promise cross-platform bit identity.
The full selected suite detected **15/15** explicit operation faults; the deliberately
weak sign-only suite detected **1/15**, retaining **14 misses**. Category counts are
retained in the JSON; these are measured synthetic probe outcomes, not general
production-model defect-detection rates.

The bounded rate/hazard/recovery search used **26 actual feasible paired evaluations**
within its 27-pair budget, two iterations and **converged=false**, with message
Maximum number of iterations has been exceeded. Its best evaluated absolute
production/challenger CVA difference was **0.339367260859337 USD**, at annual continuous
rate .04948660270306208, annual hazard .4749919723020613 and recovery .24128403146083235.
These are caller-declared synthetic ranges; no historical market plausibility,
accuracy, event probability or global-optimality claim is inferred.

The actual synthetic CVA before/after change was **-3.976455414243647 USD**. The ordered
rate/recovery bridge retained **-2.402814103888373 USD** unexplained residual from the
additional exposure movement. Materiality failed its .1 USD threshold; both actual
repeat checks passed. Materiality failure means investigate the change, not reject
an approved model. Possible-cause fingerprints and full step evidence remain visible.

## Actual verification results

- Final focused post-install checks: **131 passed in 10.93s**, including architecture
  and package metadata. The earlier focused branch run recorded **129 passed in
  17.77s**; later final targeted additions are included in the whole release suite.
- Ruff check and formatting, strict mypy **125 production Python files**, and the
  project-environment Ruff/format/mypy pre-commit hooks passed. Hooks used an ignored
  workspace configuration copy with explicit .venv/Scripts/python.exe and isolated
  PRE_COMMIT_HOME; the canonical global-python entries were not claimed to work on
  this host. The 193 Python files in src/tests/scripts were supplied to hooks.
- Isolated editable 0.10.0 installation and preliminary sdist/wheel build succeeded
  with Hatchling 1.32.4; final completion-document packaging is performed afterward.
- Windows **Python 3.13.2**, live isolated PostgreSQL 17: **1336 passed, 1 warning,
  156.60s**; **99.31% branch-inclusive coverage**. Exact totals and Linux results are
  retained in artifacts/local/phase10. The warning is the existing Starlette/httpx
  TestClient deprecation; dependency locks are unchanged and it was not suppressed.
- All eleven added production modules, including the empty adapter initializer,
  had **100% statement/branch coverage** in the actual Windows release run. This
  measures executed tests, not correctness or absence of model risk.
- HTTP health, connected readiness, version **0.10.0/10**, CLI database checks and
  early installed-image source hashing succeeded. **126 packaged production/typed
  marker files** matched frozen workspace hashes. No production code changes followed
  these successful checks. The image contains the in-progress README at build time;
  it is not claimed to contain final completion-document metadata.

Linux completion, runtime UID, cleanup and preservation inventory are recorded below.

## Final release and cleanup acceptance

Linux **Python 3.12.14**, installed production wheel with locked development tools,
read-only workspace, live isolated PostgreSQL 17: **1336 passed, 1 warning, 175.21s**.
It loaded production code from site-packages, not source PYTHONPATH. Actual Windows
and Linux combined coverage was **99.31158652827791%**: **7514 statements, 1928
branches, 34 missing statements and 31 missing/partial branches** on both platforms.
Branch-only coverage was 98.39211618257261%; the stated gate uses combined statement
and branch coverage. All new modules also report 100% in the installed Linux run.

The tested Docker image ID is `sha256:664e4fd0bf63a7594fc1afa499990a291f16a8cb29cac4623e3278d23aed789a`. Runtime UID was **10001**. HTTP
health/ready/version, live SELECT 1 and operational CLI database readiness passed.
Compose configuration validation and image build were executed. No hosted CI or
external deployment result is claimed.

The verification script's finally block removed exactly
parallax-risk-phase10-verification-api-1 and
parallax-risk-phase10-verification-postgres-1, plus
parallax-risk-phase10-verification_default network and
parallax-risk-phase10-verification_postgres_data disposable test volume. The standalone
labelled test container used --rm, deleting its development tools/coverage temporary
writable layer after needed output was saved. The **35 unrelated containers** had
identical IDs/names/project labels before and after. No normal Parallax Risk Compose
service appeared in that before inventory; the normal persistent-project scope was
never targeted. Useful **0.1.0–0.10.0** release/rollback images, shared base layers/build
cache, production data and needed artifacts are retained. No global prune, forced
image deletion, arbitrary in-container file removal or unrelated-resource stop occurred.

Documentation acceptance: **9 Markdown documents created, 64 updated**. The total
phase manifest is **25 files created, 72 updated, none removed**. All **28 canonical
ADRs** have Phase 10 reviews, including new **0026–0028**; four material decision IDs
are **0001, 0026, 0027, 0028**. Sixteen historical ADR/phase/maintenance records remain
byte-identical. Dependency locks, notebooks, cleanup script and docs checker are
unchanged. Only existing production metadata files changed; financial calculations
in earlier implementation phases retain their tested code/policies.

Architecture/workflow changes are injected isolated mutations, bounded paired-model
search and actual repeat/ordered counterfactual diagnostics; no new runtime service
or persistence. New terminology and assumptions are listed above and in the glossary.
Corrected inconsistencies include stale current-scope/API/release markers, future
mutation deferrals, broken decision-table continuity, editable metadata mismatch,
daily CSA fixture names/horizon and SciPy's misleading callback exception wrapper.
Historical helpers now explicitly require matching source archives for replay; the
older validation demo label is distinguished from current installed release identity.

Verified commands include Ruff check/format, strict mypy, all three project-environment
pre-commit hooks, docs checker, isolated editable installation, build,
`python scripts/demo_adversarial.py` with byte replay, focused test command and
`scripts/verify_phase10.ps1`. The helper executes Compose config/up/build, HTTP
health/ready/version, operational check-db, full Windows pytest, installed-wheel Linux
pytest, source hashing and runtime UID, then ownership-checked cleanup. Final scoped
inventory and completion-document package integrity are retained in artifacts/local/phase10.
Detailed Phase 11 governance/monitoring/lineage/reporting and Phase 12 financial API/
production hardening pages are deferred. Phase 10 completion does not implement them.
