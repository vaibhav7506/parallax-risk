# Parallax Risk — Phase 5 implementation and verification

**Phase 5 complete; release 0.5.0; 2026-10-01.** Completed phases: 1–5 of 12.
Phase 6 exposure engine/WWR and later CVA/XVA remain NOT IMPLEMENTED and require
another `go`. This report records new execution; it does not relabel the historical
Phase 1–4 tests. [Methodology](../methodology/PORTFOLIO_COLLATERAL.md),
[workflow](../workflows/PORTFOLIO_WORKFLOW.md), [tutorial](../tutorials/04-FIRST-PORTFOLIO-RUN.md),
[decision ledger](../decisions/README.md).

## Implemented behavior

Immutable PortfolioSnapshot → Counterparty → NettingSet → Trade, multiple legal
entities/scopes, existing instrument currencies, signed Decimal positions and
booking/effective/termination metadata. Snapshots retain opaque identity/version
and full content hashes, with unique global trade/set/entity/CSA IDs and sorted
immutable collections. Forward-start contracts are eligible from booking; final
payment/termination on valuation day is excluded. Exit cash must be booked explicitly.

An injected PortfolioPricer/PortfolioService composes the existing deterministic
engine and verifies all pricing date/currency/instrument/market/curve evidence.
Gross/no-netting and enforceably netted positive/negative values are calculated per
set. Counterparty/portfolio risk magnitudes add across scopes; accounting values
never authorize cross-scope collateral or netting. Empty books/scopes are supported.

CSA declares directional thresholds, MTA, signed reusable title-transfer independent
amount, eligible cash currencies and haircuts, fixed calendar call frequency, lag,
MPOR and one-way/two-way exchange. A physical cash account retains opening balances
and dated uniquely identified movements. Settled collateral offsets current V;
known pending transfers affect the next instruction only, preventing duplicates.
Full differences transfer only when |difference| is strictly greater than MTA.
Effective-value instructions do not execute or implicitly allocate nominal cash.

Direct FX conversion adjusts the declared spot settlement date using explicit
currency discount curves. Signed cash is valued with caller-supplied haircuts.
The deterministic MPOR scenario freezes physical settled balances at default-day
end, ignores later settlements/calls and revalues foreign cash at the exact closeout
endpoint. No pathwise repricing, stochastic exposure metrics or default losses are added.

Release/API/CLI/Compose metadata is 0.5.0/phase 5. Existing deterministic/calibration/
simulation mathematical versions remain 0.2.0/0.3.0/0.4.0. No dependency range/lock,
model equation, notebook, financial API, database table or migration changed.

## Actual verification

| Check | Actual environment/result |
|---|---|
| Full Windows suite | Python 3.13.2, live isolated PostgreSQL 17: **742 passed**, one warning, 70.92 s |
| Full Linux suite | Python 3.12.14, installed production wheel in disposable 0.5.0 container, live isolated PostgreSQL 17: **742 passed**, one warning, 77.55 s |
| Branch-inclusive coverage, each full suite | **99.26%**; 4,237 statements, 1,046 branches; 19 missing statements / 20 partial branches; required gate >=95% passed |
| New portfolio application/domain coverage | 100% statements and branches in all six new production modules on both platforms |
| New tests | 89 additional collected cases; initial focused 84 passed, expanded focused 87 passed, final additions exercised in both full suites |
| Ruff / format | All checks passed; 214 files formatted (80 source + 38 tests + 8 Python scripts + 86 Markdown + 2 notebooks) |
| Strict mypy | All 80 source files passed |
| Pre-commit | Project-environment Ruff, format and mypy hooks all passed |
| Documentation checker | 86 Markdown files, 13 canonical ADRs, 593 concrete references; all local links/index reachability and completed-phase histories passed |
| Synthetic portfolio demo | Production service, full labelled input/result JSON; two subprocess stdout runs were byte-identical |
| Packaging | 0.5.0 source archive and wheel built with isolated Hatchling 1.32.4; wheel version/typed marker/new modules/README scope inspected; final source archive refreshed with completion records |
| PowerShell helper | Parsed successfully; executed with saved results and mandatory cleanup in finally |
| Runtime/API/DB | `/health` ok, `/ready` connected, `/version` correct 0.5.0/phase 5; container CLI check-db connected; production runtime UID 10001 |

Quantitative tests use exact Decimal targets for legal sums, thresholds/MTA equality,
pending/settled state, haircut .2 and one-way returns. Independent settlement-adjusted
FX and discounted foreign-position targets use relative tolerance 1e-14. Hypothesis
exercises 80 generated netting-bound/received-collateral-monotonicity cases. MPOR
cases cover 0/2/10 calendar days, pending settlement freeze, changed closeout FX,
wrong endpoints and currency rejection. Lifecycle, negative positions, no-netting,
cross-set/counterparty separation, invalid scope/CSA/ledger IDs and malformed pricer
lineage are exercised. Existing test coverage exclusions and tests were retained.

The warning in each full suite is the existing Starlette/httpx TestClient deprecation.
Docker pip root warnings occur only during image build/disposable dev installation;
production runs UID 10001. No skipped PostgreSQL test is counted as live verification.
Python 3.14 and hosted CI were not executed. No benchmark/speed/regulatory claim is made.

Executed commands included `python scripts/demo_portfolio.py`, `parallax-risk version`,
`python scripts/check_docs.py`, Ruff lint/format, strict mypy, pre-commit, `python -m build`,
`python -m coverage json` and `.\scripts\verify_phase5.ps1`. The helper validates
Compose, builds/starts the isolated stack, tests both platforms and invokes
`scripts/cleanup_docker.ps1 -Phase 5 -Apply` in finally. Final release hashes and detailed
logs are retained locally; no source commit is fabricated.

## Assumptions, limits and terminology

Legal enforceability is caller attestation. Lifecycle is end-of-day whole-trade
eligibility, not automatic settlement/novation. Cash only; symmetric signed haircuts,
direct FX orientation and supported curve horizons. Exact-contract Decimal arithmetic
is separate from binary64 pricing/conversion, and excess precision fails explicitly.

IA is reusable title-transfer collateral, not segregated regulatory IM. Strict-greater
MTA and calendar-day timing are declared research policies, not universal CSA/regulatory
rules. Physical allocation, confirmed movements and settlement rounding are caller
responsibilities. No interest, securities, liquidation, disputes, failed settlements,
funding/custody/segregation, IM estimator, legal recovery or regulatory MPOR is inferred.
MPOR uses caller-chosen default/closeout values, not default simulation. Read the
[full equations and primary reference context](../methodology/PORTFOLIO_COLLATERAL.md).

New glossary terms include portfolio snapshot, legal netting scope, signed quantity,
effective-date metadata, gross/net positive risk, CSA, VM, independent amount, MTA,
settled/pending collateral, haircut-adjusted value and calendar MPOR. Architecture
adds domain legal/cash policies plus an application pricer port; operational resource
composition and persistence remain unchanged.

## Documentation and decisions

**6 Markdown documents created; 47 updated.** The six new documents are methodology,
workflow, tutorial, this evidence report and ADRs 0012/0013. All 13 canonical ADRs
have a Phase 5 review row, preserving prior rows; 0001/0002 document new composition/
Money usage and 0012/0013 the legal/lifecycle and collateral policies. Four material
implementation decision extensions/additions are counted in the canonical ledger.
No ADR is superseded; existing model/sequence/persistence choices remain accepted.

README, AGENTS, ROADMAP, CHANGELOG, INDEX, CODEBASE_GUIDE, WORKFLOW, DOMAIN_MODEL,
GLOSSARY, LIMITATIONS, reproducibility, methodology, testing, architecture and
operations guides were reviewed/synchronized. API examples show actual release/phase.
Stale absent-portfolio/collateral/lineage statements and the current helper/version
were corrected. Historical descriptions are preserved; simulation remains separate
from deterministic portfolios. The decision ledger/ADR phase rows now form continuous
Markdown tables. Historical `docs/adr` and Phase 1–4/maintenance reports remain byte-
identical to the retained 0.4.0 archive (11 protected Markdown files).

Detailed stochastic exposure/WWR, CVA/XVA/capital, governance, financial API/security/
scale and segregated-IM/securities collateral documents remain deferred. No empty
future model page or next-phase implementation is created.

## Docker resources retained and removed

The exact disposable project was `parallax-risk-phase5-verification`, with ownership
checked by the existing cleanup script. Removed api/postgres verification services,
`parallax-risk-phase5-verification_default` network and
`parallax-risk-phase5-verification_postgres_data` test volume. The labelled
`parallax-risk-phase5-tests` container used `--rm`; its installed dev packages,
coverage/cache and temporary writable files disappeared with it. No arbitrary
inside-container file deletion was performed. Post-session resource queries show
zero remaining Phase 5 containers/networks/volumes.

All **35 other containers** retain identical ID/name/project rows before/after.
Normal Parallax Risk database resources were never targeted. Useful release/rollback
images 0.1.0–0.5.0, shared base layers/build cache, source archives/wheels, logs and
replay evidence remain. No global/system/image/volume/builder prune or force image
removal occurred. Current image identity:
`sha256:f2c15471cf44edd776687f744667a7a9130b22ed1d8a00f151dac1fd23775261`.

Useful local evidence is under `artifacts/local/phase5/`: both pytest logs, Windows
coverage/environment JSON, endpoint/version/UID/image results, before/after and
cleanup logs, cleanup summary, synthetic portfolio JSON, archive hash/manifest data.
Ephemeral Docker dev files were removed with their container; persisted evidence is retained.

## File manifest

**18 created, 56 updated, 0 removed** relative to the retained 0.4.0 source archive;
generated archive-only PKG-INFO is excluded. These are file counts, not commit counts.
The full manifest is also retained as local JSON.

### Created

- `docs/decisions/0012-legal-portfolio-snapshots.md`
- `docs/decisions/0013-collateral-ledger-and-margin-policy.md`
- `docs/methodology/PORTFOLIO_COLLATERAL.md`
- `docs/tutorials/04-FIRST-PORTFOLIO-RUN.md`
- `docs/validation/phase-5.md`
- `docs/workflows/PORTFOLIO_WORKFLOW.md`
- `scripts/demo_portfolio.py`
- `scripts/verify_phase5.ps1`
- `src/parallax_risk/application/portfolio.py`
- `src/parallax_risk/domain/portfolio/__init__.py`
- `src/parallax_risk/domain/portfolio/collateral.py`
- `src/parallax_risk/domain/portfolio/contracts.py`
- `src/parallax_risk/domain/portfolio/csa.py`
- `src/parallax_risk/domain/portfolio/netting.py`
- `tests/fixtures/portfolio.py`
- `tests/integration/test_portfolio_workflow.py`
- `tests/quantitative/test_collateral_netting.py`
- `tests/unit/test_portfolio_contracts.py`

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
- `docs/decisions/README.md`
- `docs/methodology/INDEX.md`
- `docs/methodology/deterministic-pricing.md`
- `docs/methodology/primitives.md`
- `docs/operations/CONFIGURATION.md`
- `docs/operations/DATABASE.md`
- `docs/operations/DOCKER.md`
- `docs/operations/LOCAL_SETUP.md`
- `docs/operations/OBSERVABILITY.md`
- `docs/operations/RELEASE.md`
- `docs/operations/TROUBLESHOOTING.md`
- `docs/testing/STRATEGY.md`
- `docs/validation/OVERVIEW.md`
- `docs/workflows/SIMULATION_WORKFLOW.md`
- `pyproject.toml`
- `src/parallax_risk/__init__.py`
- `src/parallax_risk/api/schemas.py`
- `src/parallax_risk/cli/main.py`
- `src/parallax_risk/common/identifiers.py`
- `tests/api/test_operations.py`
- `tests/integration/test_database_cli.py`
