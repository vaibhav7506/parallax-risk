# Parallax Risk — Phase 6 implementation and verification

**Phase 6 complete; release 0.6.0; 2026-10-01.** Completed phases: 1–6 of 12.
Phase 7 XVA and extended sensitivities remain NOT IMPLEMENTED and require another
`go`. This report records actual new execution; earlier outcomes remain historical.

[Exposure](../methodology/EXPOSURE.md), [credit](../methodology/CREDIT_DEFAULT.md),
[WWR](../methodology/WRONG_WAY_RISK.md), [workflow](../workflows/EXPOSURE_WORKFLOW.md),
[tutorial](../tutorials/05-FIRST-EXPOSURE-RUN.md), [decisions](../decisions/README.md).

## Implemented behavior

An injected ExposureService consumes immutable simulation batches, builds conditional
Q markets, reprices actual existing instruments through PortfolioService and retains
positive/negative exposure arrays per counterparty. Conditional Vasicek/HullWhite bond
curves use current state, explicit knots and no extrapolation. FX binds direct Q GBM
QUOTE/BASE states. Exact civil-date ACT/365F grids and labelled derived provenance
are required. Known origin fixings are supplied; future grid fixings are generated
once and retained without lookahead. Inactive origin trades request no future fixing.

Legal netting/collateral remain per set. Each path owns separate cash history. The
restricted simulator policy settles full effective instructions perfectly in zero-
haircut CSA currency on daily calendar grids. Pending calls prevent duplicate calls;
only settled cash offsets exposure. Zero-lag settlement affects that day's profile.
The generic Phase 5 physical ledger and standalone frozen MPOR stay separate.

EE/ENE include zero paths, PFE uses retained-sample linear quantiles with configurable
levels, and EPE averages trapezoidal EE over the full supplied horizon. Total profiles
use pathwise sums across legal scopes; no cross-entity netting or sum of PFE is inferred.
The output cap applies to two exposure matrices, not total/peak memory.

Supplied piecewise hazard/survival/default curves have exact interval integration and
finite-horizon inversion, no extrapolation, and constant recovery assumptions. Owned
separate exponential thresholds implement deterministic independent defaults. Static
full-path rank stress preserves every sampled threshold. Dynamic scenarios bind
correlated Q GBM credit spreads and an injectable spread-to-intensity policy, integrate
left-grid hazard and report mean conditional survival separately from the baseline.
ReducedFormSpread declares the credit-triangle approximation, not CDS calibration.

Grid EAD uses the first endpoint >= default, retaining alive-path collateral and zeros
for nondefaults. It omits default-conditioned freeze/MPOR, interpolation, discounting
and recovery loss. Comparison records default counts/PD, unconditional and conditional
means, difference and ratio; no-default conditional mean or zero-baseline ratio is None.
This is research exposure representation, not regulatory EAD/effective EPE or CVA.

Release/API/CLI/Compose metadata is 0.6.0/phase 6. Existing deterministic/calibration/
simulation mathematical versions remain 0.2.0/0.3.0/0.4.0. No existing model equation, dependency
range/lock, notebook, database table/migration or financial API is changed.

## Actual verification

| Check | Actual environment/result |
|---|---|
| Full Windows suite | Python 3.13.2, live isolated PostgreSQL 17: **821 passed**, one warning, 103.56 s |
| Full Linux suite | Python 3.12.14, installed production wheel in disposable 0.6.0 container, live isolated PostgreSQL 17: **821 passed**, one warning, 107.83 s |
| Branch-inclusive coverage | **99.37%** in each full suite; 4,910 statements, 1,284 branches; 19 missing statements and 20 partial branches; required >=95% gate passed |
| New production modules | 100% statements/branches in all new Phase 6 production modules in each full suite |
| New tests | 79 additional collected cases; final focused suite 79 passed in 10.62 s |
| Ruff / format | All checks passed; 236 files already formatted in final check |
| Strict mypy | All 89 source files passed |
| Pre-commit | Project-environment Ruff, format and mypy hooks all passed |
| Documentation checker | 95 Markdown files, 16 canonical ADRs, 693 concrete references; all local links/index reachability and completed-phase ADR histories passed |
| Synthetic demo | Two actual subprocess stdout runs byte-identical: 124,778 bytes, SHA-256 edf0867eefdf808734a914e2611a231f17e164c6b95f03ce85fe132db0e75f06 |
| Packaging | 0.6.0 wheel and source archive built with isolated Hatchling 1.32.4; version/typed marker/new modules/README inspected; completion source archive refreshed |
| Helper | Phase 6 PowerShell helper parsed and executed; finally cleanup saved outside containers |
| API/runtime/DB | /health ok, /ready connected, /version 0.6.0/6; container CLI check-db connected; production UID 10001 |

Independent mathematical targets cover hazard integrals, survival/default increments,
endpoint inversion, zero hazard, tiny PD preservation and explicit overflow/default-time
resolution rejection. A 50,000-threshold known CDF test uses six analytical binomial
standard errors. A 20,000-path correlated dynamic experiment checks default frequency
against mean conditional survival and isolates dependence by independently permuting
whole credit histories; the empirical credit/survival marginal is preserved. The
selected positive-correlation case increases default-weighted exposure by at least 15%,
without claiming universal monotonicity. Static thresholds retain their exact sampled
marginal and rho=0 reproduces the baseline.

Actual future FX-forward EE across 2,048 paths is compared with its analytic lognormal
positive part within six sample standard errors. Conditional HullWhite knots use
relative 1e-14; hazard identities use 1e-15. Hand summaries test empirical PFE and
trapezoidal EPE exactly within declared finite tolerances. Sixty generated cases check
PFE monotonicity in quantile and eligible received-collateral monotonicity. Workflow
checks cover no-credit/default/zero exposure, lifecycle maturity, legal-scope separation,
netting, daily cash lag 0/1/2, fixing retention, batch replay, malformed adapters,
unique random addresses, custom spread policy and invalid inputs. Neither EE nor PFE
is required to increase with time. Existing tests/coverage exclusions were preserved.

The warning is the existing Starlette/httpx TestClient deprecation. Pip root warnings
occur only in build/disposable dev installation; production UID is 10001. No PostgreSQL
skip is counted as live evidence. Python 3.14 and hosted CI were not executed. No market
accuracy, regulatory certification or performance benchmark claim is made. Early test
harness corrections and missing example import were fixed before both full suites.

Verified commands include `python scripts/demo_exposure.py`, `parallax-risk version`,
`python scripts/check_docs.py`, Ruff check/format, strict mypy, project pre-commit,
`python -m build`, `python -m coverage json` and `.\scripts\verify_phase6.ps1`.
The helper validates Compose, starts the isolated stack, checks runtime/API/database,
runs both full suites and calls `scripts/cleanup_docker.ps1 -Phase 6 -Apply` in finally.
Release hashes, JSON replay, coverage and detailed logs are retained locally. There
is no source commit in this workspace; none is fabricated.

## Assumptions, limitations and terminology

Explicit Q binding/units do not establish arbitrage consistency for arbitrary
stochastic-rate FX. Caller drift consistency, single-curve projection and log-linear
interpolation between supplied conditional bond knots remain assumptions. Derived
snapshots are synthetic/model values, not observed market quotes. Origin fixings,
legal enforceability and supplied credit/recovery remain caller evidence/assumptions.

Perfect cash settlement uses CSA-currency zero-haircut cash and calendar dates; no
interest, funding, disputes, failed settlement, segregated IM or business-day calendar
is added. Right-grid EAD can be biased near maturity and does not freeze calls at
default or apply MPOR. Static rank stress is non-adapted; dynamic intensities are
left-grid, uncalibrated to baseline survival and use a declared spread approximation.
There is no stochastic recovery, bilateral default, CDS calibration, regulatory EAD,
CVA/DVA/FVA/MVA, XVA sensitivities, capital or institutional model approval.

New glossary terms: EE, ENE, horizon EPE, empirical PFE, grid EAD, hazard/intensity,
survival, recovery/LGD, Cox threshold, static rank WWR, dynamic WWR, credit triangle
and conditional market path. Full definitions and numerical conventions appear in
the actual methodology pages, not empty future model scaffolds.

## Documentation and decisions

Created nine Markdown files: three methodology guides, an exposure workflow, a first
exposure tutorial, this phase report and ADRs 0014–0016. Updated 54 existing Markdown
files including every canonical decision, the register and affected project/navigation,
domain, reproducibility, methodology, testing, architecture, API and operations guides.
Every one of 16 ADRs has a Phase 6 row; unchanged policies explicitly say reviewed/no
change. Material IDs are 0001, 0003, 0014, 0015 and 0016: five changes, three new IDs.
These extend prior policies; none replaces/supersedes an earlier accepted policy.

All 12 historical phase/maintenance/`docs/adr` records are byte-identical to the retained
0.5.0 archive. The report manifest uses SHA-256 comparison with that archive because
all project files are untracked in the current Git workspace. Prior phase test counts
are preserved. Corrected stale README/domain/methodology exposure claims, the portfolio
hash row in reproducibility and correlation's deferred-exposure wording. Documentation
maintenance never increments the implementation count.

Architecture extends the inward dependency pattern with domain exposure/credit and
injected application composition. No runtime service, resource lifetime or database
schema is added. The workflow now supports path-local future markets, fixings and cash
before empirical/default summaries. XVA/capital/lab/governance/production tutorials,
credit calibration, arbitrage-consistent joint stochastic-rate FX and default-conditioned
closeout documents remain deferred until actual authorized implementation. No empty
future pages were created.

## Docker cleanup and retained evidence

The helper's finally block removed only `parallax-risk-phase6-verification-api-1`,
`parallax-risk-phase6-verification-postgres-1`, its `default` test network and
`postgres_data` disposable volume. The separately labelled `parallax-risk-phase6-tests`
container used `--rm`. Final label inventories and preview show no Phase 6 containers,
networks or volumes remaining. All **35 unrelated container IDs/names/project labels**
match the exact before/after inventory; no other workload was stopped or deleted.

Useful `parallax-risk:0.6.0` and 0.5.0/0.4.0/0.3.0/0.2.0/0.1.0 release/rollback images,
shared bases/layers/build cache, wheel/source releases, locked inputs and local logs,
coverage, replay and file hashes remain. The normal `parallax-risk` persistent database
was not selected or removed. No global system/image/volume/builder prune, force image
removal or arbitrary in-container file deletion was used. Disposable Linux dev files
were removed with its `--rm` container; useful installed release contents remain.

Current image identity: `sha256:d27481169e2b68fd002ea0745861a53819235ed1a8a263e6b72cc55401b2fb42`. Actual tag identities and ownership inventories
are retained under `artifacts/local/phase6/`; locally ignored artifacts are not a
promise of Git/persisted lineage. The unchanged cleanup script checks exact project,
workspace and attachments; ambiguous ownership would be retained/reported.

## File manifest

Compared with the retained 0.5.0 source archive: 23 files created, 62 updated, none removed. Documentation: 9 Markdown files created, 54 updated. This is source/content comparison, not a Git commit count.

### Created

- `docs/decisions/0014-conditional-market-paths.md`
- `docs/decisions/0015-credit-default-dependence.md`
- `docs/decisions/0016-exposure-statistics-and-cash-policy.md`
- `docs/methodology/CREDIT_DEFAULT.md`
- `docs/methodology/EXPOSURE.md`
- `docs/methodology/WRONG_WAY_RISK.md`
- `docs/tutorials/05-FIRST-EXPOSURE-RUN.md`
- `docs/validation/phase-6.md`
- `docs/workflows/EXPOSURE_WORKFLOW.md`
- `scripts/demo_exposure.py`
- `scripts/verify_phase6.ps1`
- `src/parallax_risk/application/exposure.py`
- `src/parallax_risk/application/exposure_examples.py`
- `src/parallax_risk/domain/credit/__init__.py`
- `src/parallax_risk/domain/credit/dependence.py`
- `src/parallax_risk/domain/credit/hazard.py`
- `src/parallax_risk/domain/exposure/__init__.py`
- `src/parallax_risk/domain/exposure/contracts.py`
- `src/parallax_risk/domain/exposure/markets.py`
- `src/parallax_risk/domain/exposure/statistics.py`
- `tests/fixtures/exposure.py`
- `tests/integration/test_exposure_workflow.py`
- `tests/quantitative/test_credit_exposure.py`

### Updated

- `AGENTS.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `DEVELOPMENT.md`
- `Makefile`
- `README.md`
- `ROADMAP.md`
- `SECURITY.md`
- `docker-compose.yml`
- `docs/CODEBASE_GUIDE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/GLOSSARY.md`
- `docs/INDEX.md`
- `docs/LIMITATIONS.md`
- `docs/REPRODUCIBILITY.md`
- `docs/WORKFLOW.md`
- `docs/api/ENDPOINTS.md`
- `docs/api/ERRORS.md`
- `docs/api/OVERVIEW.md`
- `docs/architecture/COMPONENTS.md`
- `docs/architecture/DATA_FLOW.md`
- `docs/architecture/DEPENDENCY_RULES.md`
- `docs/architecture/DEPLOYMENT.md`
- `docs/architecture/OVERVIEW.md`
- `docs/decisions/0001-clean-architecture.md`
- `docs/decisions/0002-money-representation.md`
- `docs/decisions/0003-immutable-market-snapshots.md`
- `docs/decisions/0004-random-sequence-reproducibility.md`
- `docs/decisions/0005-correlation-validation.md`
- `docs/decisions/0006-persistence-boundaries.md`
- `docs/decisions/0007-deterministic-curves-and-pricing.md`
- `docs/decisions/0008-stochastic-models-and-discretization.md`
- `docs/decisions/0009-bounded-calibration-and-uncertainty.md`
- `docs/decisions/0010-independent-sampling-units.md`
- `docs/decisions/0011-batched-paths-and-gaussian-covariance.md`
- `docs/decisions/0012-legal-portfolio-snapshots.md`
- `docs/decisions/0013-collateral-ledger-and-margin-policy.md`
- `docs/decisions/README.md`
- `docs/methodology/CORRELATION.md`
- `docs/methodology/INDEX.md`
- `docs/methodology/MARKET_DATA.md`
- `docs/methodology/MONTE_CARLO.md`
- `docs/methodology/MONTE_CARLO_STATISTICS.md`
- `docs/methodology/PORTFOLIO_COLLATERAL.md`
- `docs/methodology/deterministic-pricing.md`
- `docs/operations/CONFIGURATION.md`
- `docs/operations/DATABASE.md`
- `docs/operations/DOCKER.md`
- `docs/operations/LOCAL_SETUP.md`
- `docs/operations/OBSERVABILITY.md`
- `docs/operations/RELEASE.md`
- `docs/operations/TROUBLESHOOTING.md`
- `docs/testing/STRATEGY.md`
- `docs/validation/OVERVIEW.md`
- `docs/workflows/PORTFOLIO_WORKFLOW.md`
- `docs/workflows/SIMULATION_WORKFLOW.md`
- `pyproject.toml`
- `src/parallax_risk/__init__.py`
- `src/parallax_risk/api/schemas.py`
- `src/parallax_risk/cli/main.py`
- `tests/api/test_operations.py`
- `tests/integration/test_database_cli.py`

