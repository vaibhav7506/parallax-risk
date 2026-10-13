# Parallax Risk — Phase 8 implementation and verification

**Phase 8 complete; release 0.8.0; 2026-10-01.**
Completed implementation phases: 1–8 of 12.
Phase 9 model validation lab is NOT IMPLEMENTED and requires another `go`.

[Standardized prototype](../methodology/STANDARDIZED_CCR.md),
[IMM challenger](../methodology/IMM_CHALLENGER.md),
[comparison](../methodology/CCR_COMPARISON.md),
[workflow](../workflows/CCR_WORKFLOW.md),
[tutorial](../tutorials/07-FIRST-CCR-COMPARISON.md), [decisions](../decisions/README.md).

## Implementation and assumptions

Restricted linear domestic IRS/domestic-quote FX mapping, source-labelled
supervisory configuration, explicit business-day MPOR/NICA, RC/PFE/add-on/alpha
and margined/unmargined EAD cap. IR aggregation recognizes within-bucket offsets
and sums absolute bucket totals without cross-bucket offset. Other asset-class
enumerations describe unsupported treatments and reject. Decimal Money boundaries
do not imply exact-decimal valuation. Legal enforceability is caller attestation.

Actual Monte Carlo exposure is replayed separately per legal unit with scoped
ledgers and common addressed streams. Exact first-year/final-maturity nodes feed
running-max effective EE and normalized right-endpoint EPE/effective EPE.
Matching results give EAD, illustrative RWA/capital differences, trade/group
drivers, arithmetic component bridges/residuals and strict dual-threshold exceptions.
Zero reference relative ratio is null. No causal attribution is claimed.

These are research prototypes, without regulatory compliance, supervisory model
approval, complete/current-stressed IMM, local capital rulebook, regulatory collateral
eligibility or default-frozen MPOR closeout. Phase 6 simulation restrictions remain.
No new dependency/lock, notebook, model equation for earlier phases, database
schema/migration, financial API or runtime service is introduced. Existing pricing,
calibration, simulation and XVA model versions remain .2/.3/.4/.7 respectively.

## Verification

| Check | Actual environment/result |
|---|---|
| Full Windows suite | Python 3.13.2, live isolated PostgreSQL 17: **1072 passed**, one warning, 105.28 s |
| Full Linux suite | Python 3.12.14, installed production wheel in disposable 0.8.0 container, live isolated PostgreSQL 17: **1072 passed**, one warning, 138.56 s |
| Branch-inclusive coverage | **99.49%** on each platform; 6,019 statements, 1,602 branches; 19 missing statements, 20 partial branches; >=95% gate passed |
| New production modules | 100% statements/branches in every Phase 8 production module on both full runs |
| New cases | 129 new cases; focused Windows run passed in 4.35 s before both successful full runs |
| Ruff / format / strict mypy | All checks passed; formatting 279 files; strict mypy 104 source files |
| Project hooks | Ruff, format and strict mypy passed for 164 Python files with explicit project interpreter and workspace-local cache |
| Documentation | 113 Markdown files, 22 canonical ADRs; local links/references/reachability/history checks passed |
| Demo replay | Two Windows stdout runs byte-identical: 12,481 bytes; digest and actual results retained below |
| Packaging | 0.8.0 wheel/source archive built with isolated Hatchling 1.32.4; all 105 packaged source/typed-marker files byte-matched workspace; completion archive refreshed |
| Runtime/helper | Phase 8 helper parsed/executed; /health ok, /ready connected, /version 0.8.0/8; CLI check-db connected; production UID 10001 |
| Cleanup | Both failed initial and successful verification sessions ran ownership-scoped finally cleanup; final unrelated container identities unchanged (35) |

Both successful full suites executed the live PostgreSQL test; neither skipped it.
The single warning is existing Starlette/httpx TestClient deprecation. No dependency
lock change was made to suppress it. Full runs exercised actual production code;
subsequent completion edits are documentation/release evidence only. No hosted CI,
Python 3.14 execution, external market benchmark or regulatory approval is claimed.

## Documentation, decisions and terminology

Nine documents are created: three methodologies, workflow, tutorial, this report
and ADRs 0020–0022. Every earlier canonical ADR receives a Phase 8 review row;
0001 is extended, while previous history and fourteen historical records remain
unchanged. New terms: supervisory duration/maturity factor, standardized add-on/
multiplier/PFE, NICA/business-day MPOR, effective EE/EPE, illustrative RWA/capital,
dual-threshold comparison exception and arithmetic bridge. Detailed model-lab,
mutation, governance and financial-API documents are deferred with Phases 9–12.

## File manifest and Docker resources

The completion manifest compares the retained 0.7.0 source archive baseline
with final workspace files and retains SHA-256s under artifacts/local/phase8.
Only phase8-verification-owned disposable containers/network/test volume were
removed. Useful release/rollback images, base layers/cache, production data and
other projects are retained. No global prune or arbitrary in-container deletion.

## Architecture, workflow and precision review

Pure `domain/ccr` owns contracts, restricted instrument mapping, formulas,
effective-EE/EPE integration and comparison arithmetic. CcrService injects the
existing actual portfolio/exposure workflow, preserves legal-unit boundaries and
verifies book/run/market/account/simulation/date/profile/path-shape evidence.
Runtime simulation metadata is retained per scope. No new import-time dependency
initialization, global RNG/logger, resource-owning domain code or database adapter.

Standardized PFE is a formula add-on rather than an empirical quantile. Phase 6's
trapezoidal full-horizon EPE stays unchanged. Challenger averages use explicit
right endpoints and exact first-year/final-contractual-payment horizon nodes.
Future termination/reset mapping rejects. MPOR must meet the caller-configured
business-day floor. The arithmetic bridge includes margin cap and a separately
reported conversion/rounding residual. Binary64 quantitative work remains distinct
from exact Money arithmetic; no cent rounding or exact-decimal valuation claim.

## Independently targeted numerical checks

The 100 USD at-the-money FX fixture has add-on=4 and EAD=5.6. For negative net
value -1 and add-on 4, multiplier=.05+.95*exp(-1/7.6). Short FX maturity .001
hits MF=.2; daily bilateral 10/250 MPOR gives margined MF=.3 before the cap.
IR targets independently use exponential supervisory duration with explicit .04
year floor; buckets use E<1, 1<=E<=5, E>5, with no inter-bucket/currency offsets.

EE=(10,20,5) at (0,.25,1) gives EPE=8.75, effective EPE=20 and alpha=1.4 EAD=28.
The short-horizon (0,.1,.5) fixture explicitly normalizes by .5. The actual
production deterministic FX simulation target is 10*exp(-.03*(1-t)) USD before
maturity, zero at maturity. The actual domestic IRS target is
100*(expm1(.03)-.02)*exp(-.03*(1-t)) before maturity, zero at maturity. Effective
EE retains its earlier maximum through the final date. CRE99 RC benchmarks are
separately identified in the methodology. Absolute formula tolerances range from
1e-15 dimensionless to 2e-12 USD; scaled 1000x monetary homogeneity uses 1e-10 USD.
Every new approximate assertion explicitly uses relative tolerance zero.

## Commands and inconsistencies

Verified focused quantitative/contract/workflow command, Ruff/format/strict mypy,
docs checker, editable 0.8.0 install, isolated wheel/sdist build, module CLI version,
PowerShell helper parsing and two byte-identical actual demo subprocesses.
The full helper records HTTP /health, /ready, /version, actual CLI database checks,
non-root runtime and full Windows/Linux tests. Final outcomes appear in the table.

The default hook launcher resolved global Python without Ruff/mypy in this host.
The same project hooks passed with a temporary ignored configuration naming the
project interpreter and a workspace-local cache; canonical hook configuration is
unchanged. The initial no-build-isolation metadata refresh lacked Hatchling;
isolated installation/build succeeded with Hatchling 1.32.4. These failed setup
attempts do not count as successful verification.

Corrected current API metadata examples and stale active verification-project
references. The first full Windows attempt found an unchanged 0.7.0 CLI assertion:
1 failed, 1071 passed, one warning in 142.80 s; no Linux suite ran in that failed
session. Its finally cleanup succeeded and first-attempt logs remain retained.
The assertion was corrected to 0.8.0; production formulas were unchanged, and both
full suites were rerun. Historical phase results were never relabelled.

## Concrete phase file manifest

Compared with the retained 0.7.0 completion source archive: **23 created, 66 updated,
0 removed**. Documentation: **9 Markdown created, 58 updated**. Current repository:
113 Markdown files, 22 canonical ADRs, 104 source Python files, 49 test Python
files and 11 script Python files. Full final hashes are retained in
`artifacts/local/phase8/file-manifest.json`; ignored reports/build/cache files are
not counted as source changes. Fourteen historical records, dependency locks,
notebooks, Docker cleanup and documentation validators remain byte-identical.

| Action | Files |
|---|---|
| Created | `docs/decisions/0020-restricted-standardized-ccr.md` |
| Created | `docs/decisions/0021-legal-unit-imm-challenger.md` |
| Created | `docs/decisions/0022-ccr-capital-comparison.md` |
| Created | `docs/methodology/CCR_COMPARISON.md` |
| Created | `docs/methodology/IMM_CHALLENGER.md` |
| Created | `docs/methodology/STANDARDIZED_CCR.md` |
| Created | `docs/tutorials/07-FIRST-CCR-COMPARISON.md` |
| Created | `docs/validation/phase-8.md` |
| Created | `docs/workflows/CCR_WORKFLOW.md` |
| Created | `scripts/demo_ccr.py` |
| Created | `scripts/verify_phase8.ps1` |
| Created | `src/parallax_risk/application/ccr.py` |
| Created | `src/parallax_risk/application/ccr_examples.py` |
| Created | `src/parallax_risk/domain/ccr/__init__.py` |
| Created | `src/parallax_risk/domain/ccr/challenger.py` |
| Created | `src/parallax_risk/domain/ccr/comparison.py` |
| Created | `src/parallax_risk/domain/ccr/contracts.py` |
| Created | `src/parallax_risk/domain/ccr/mapping.py` |
| Created | `src/parallax_risk/domain/ccr/standardized.py` |
| Created | `tests/fixtures/ccr.py` |
| Created | `tests/integration/test_ccr_workflow.py` |
| Created | `tests/quantitative/test_ccr.py` |
| Created | `tests/unit/test_ccr_contracts.py` |
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
| Updated | `docs/decisions/README.md` |
| Updated | `docs/methodology/EXPOSURE.md` |
| Updated | `docs/methodology/INDEX.md` |
| Updated | `docs/methodology/MARKET_DATA.md` |
| Updated | `docs/methodology/PORTFOLIO_COLLATERAL.md` |
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
| Updated | `docs/workflows/EXPOSURE_WORKFLOW.md` |
| Updated | `docs/workflows/PORTFOLIO_WORKFLOW.md` |
| Updated | `pyproject.toml` |
| Updated | `src/parallax_risk/__init__.py` |
| Updated | `src/parallax_risk/api/schemas.py` |
| Updated | `src/parallax_risk/cli/main.py` |
| Updated | `tests/api/test_operations.py` |
| Updated | `tests/integration/test_database_cli.py` |

## Verified synthetic comparison interpretation

Two actual Windows demo subprocesses produced identical 12,481-byte stdout,
SHA-256 f87a8d54c7693c0b380dfa97964ef9e5e49087dd2f4c01e9156e2de3d03f5b45.
The sample reports standardized EAD 6.16000000000002 USD and challenger EAD
22.67563970794735 USD, with difference 16.51563970794733 USD and a comparison
exception under its explicit policy. The approximately -1.05e-16 USD component
bridge residual remains visible. These are labelled finite synthetic path results,
not market measurements, regulatory findings or model-accuracy evidence. The
at-the-money origin NPV retains about 1.4e-14 USD binary64 rounding residual;
it is not silently clamped to zero. Replay digest includes runtime metadata and
is a same-environment result, not a cross-platform bit-equality claim.

## Actual Docker removal and retention

Both verification sessions removed only the owned API and PostgreSQL containers,
parallax-risk-phase8-verification_default network and
parallax-risk-phase8-verification_postgres_data volume in finally. The successful
session's explicitly labelled parallax-risk-phase8-tests container used --rm;
its temporary writable files disappeared at exit. Required reports were retained
outside those writable layers. The final ownership preview found zero containers,
networks or disposable volumes for this exact verification project.

The tested retained 0.8.0 image is
sha256:e19a984f52be51c6c02b6b3fc11312dea8850c5f0e4cdcd803377aeaa062c4cc.
All useful 0.1.0–0.7.0 rollback/evidence images remain; exact identities are in
artifacts/local/phase8/retained-images.log. Shared base layers/build cache, needed
source/wheel/replay/coverage artifacts and production data are retained. No global
prune, force-image removal, arbitrary in-container deletion or other-project
operation was used. All 35 unrelated container identities match before/after.
Normal Compose parallax-risk database resources were outside cleanup scope.

The completion wheel/source archive includes final documentation; the retained
Docker image is the installed-wheel image used in the full Linux verification.
All packaged production source/typed-marker bytes match the final workspace;
completion changes after testing are documentation metadata/evidence only.
Final source archive/wheel SHA-256s and file hashes are retained in
artifacts/local/phase8/release-integrity.json and file-manifest.json. This workspace
has no source commit; retained archives/hashes supply the actual completion manifest.
