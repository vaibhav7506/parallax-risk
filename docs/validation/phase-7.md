# Parallax Risk — Phase 7 implementation and verification

**Phase 7 complete; release 0.7.0; 2026-10-01.** Completed phases: 1–7 of 12.
Phase 8 regulatory-style capital/challengers remain NOT IMPLEMENTED and require
another `go`. Actual new execution appears below; historical reports remain unchanged.

[XVA](../methodology/XVA.md), [funding](../methodology/FUNDING_MARGIN.md),
[risk](../methodology/XVA_SENSITIVITIES.md), [workflow](../workflows/XVA_WORKFLOW.md),
[tutorial](../tutorials/06-FIRST-XVA-RUN.md), [decisions](../decisions/README.md).

## Implemented behavior

Immutable domain funding/IM/own-credit contracts and four signed XvaComponents form
XvaResult, with checked total adjustment, FCA/FBA, labelled contributions, input
fingerprints, methodology and assumptions. Components require one currency and
CVA/DVA/FVA/MVA order. CVA/MVA are nonpositive, DVA nonnegative; FVA=-FCA+FBA
may have either sign. Pricing/simulation remain binary64; unrounded Decimal Money
outputs do not imply exact-decimal integration.

Independent unilateral CVA integrates deterministic-discount EE against exact
piecewise survival decrements, with endpoint-average discounted exposure on the
profile/discount/hazard knot union. Own unilateral DVA uses independent own hazard
and ENE payable magnitude. Dependent counterparty cases instead average actual
sampled default-bucket discounted EAD times LGD, including nondefault zeros. No
second PD multiplier, counterparty-survival filter or first-to-default recursion
is inferred. Right-grid alive collateral retains its Phase 6 freeze/MPOR limitation.

Funding spreads are nonnegative annual excess decimals above the discount benchmark,
piecewise constant without extrapolation. FCA/FBA use alive EE/ENE borrowing/lending
proxies; lending benefit is explicitly enabled/disabled. MVA separately funds an
externally supplied expected segregated posted IM profile, distinct from reusable
CSA independent amount and excluded from FCA. Discounted amounts use trapezoids
on the knot union; all profile/curve currency, origin, grid and horizon assumptions
are validated. No recursive funding or regulatory IM model is inferred.

XvaService injects the calculator, verifies exact exposure/run/credit and calculator
input evidence, and aggregates separate legal-entity results. Per-name labels are
intervals; aggregate labels are counterparties. XvaRevaluation invokes actual
production ExposureService/PortfolioService for every input movement. Seven factor
kinds cover rate, direct FX spot, declared rate/GBM volatility, credit-triangle
spread, recovery, Brownian correlation and existing CSA receive threshold.

Five valuations at 0, +/-h and +/-h/2 retain component/TOTAL derivatives, units and
actual stability differences. Rate movements preserve the declared FX drift change;
origin fixings stay fixed. Existing correlation factor order and PSD tolerance are
preserved. Unsupported Heston vega, custom dynamic-credit transformations and
single-name shared-spread movements reject rather than fall back. Fixed market,
default and rank stream addresses support common random numbers. Funding/external
IM stay fixed during these sensitivities.

Ordered attribution reprices every named movement and independently values the
actual endpoint. Component/total unexplained residual is always reported; a complete
ladder reconciles, while omitted factors remain visible. Interactions depend on
order; this is not Shapley or causal allocation.

Release metadata is 0.7.0/phase 7 and the new XVA model version is 0.7.0. Existing
deterministic/calibration/simulation mathematics retain 0.2.0/0.3.0/0.4.0. No dependency
range/lock, notebook, existing model equation, table/migration, financial API or new
runtime service is added. The synthetic example uses actual production paths,
supplied inputs and fixed metadata, without a fabricated source commit.

## Actual verification

| Check | Actual environment/result |
|---|---|
| Full Windows suite | Python 3.13.2, live isolated PostgreSQL 17: **943 passed**, one warning, 326.21 s |
| Full Linux suite | Python 3.12.14, installed production wheel in disposable 0.7.0 container, live isolated PostgreSQL 17: **943 passed**, one warning, 184.42 s |
| Branch-inclusive coverage | **99.44%** on each platform; 5,528 statements, 1,468 branches; 19 missing statements, 20 partial branches; required >=95% gate passed |
| New production modules | 100% statements/branches in every Phase 7 production module on both full runs |
| New cases / strict final reruns | 122 new cases; after tightening absolute-only XVA assertions, all 122 passed again on Windows (13.65 s) and installed Linux wheel (27.67 s) |
| Ruff / format | All current checks passed |
| Strict mypy / pre-commit | All 96 source files passed; project Ruff/format/mypy hooks passed |
| Documentation | 104 Markdown files and 19 canonical ADRs; final link/reference/reachability/history check passed |
| Synthetic demo | Two actual subprocess stdout runs byte-identical: 90,563 bytes; SHA-256 ae0b466ff6d3118e73d0ab73dc6ce4728b1af688e9ec795ba06d9f371881796d |
| Packaging | 0.7.0 wheel/source archive built with isolated Hatchling 1.32.4; version, typed marker and new modules inspected; completion archive refreshed |
| Helper / runtime | Phase 7 PowerShell helper parsed/executed; /health ok, /ready connected, /version 0.7.0/7; CLI check-db connected; production UID 10001 |

Independent constant-exposure targets use CVA=60*(1-exp(-0.4)),
DVA=30*(1-exp(-0.2)), FCA=2, FBA=0.5, FVA=-1.5 and MVA=-0.4 USD over two years.
They check component/total reconciliation, zero default/full recovery/zero exposure,
benefit opt-out and external IM separation. A constant-exposure flat-discount credit
integral has a closed-form target; 16/32/64/128 refinements require final error <2e-5
USD and successive error ratio >3.9. Piecewise hazard/funding knots are checked.
Sampled three-path losses produce 4+6=10 USD, including a nondefault zero and no
second PD weight. Sixty generated constant-exposure cases check only justified
hazard/recovery monotonicity.

Actual-path tests cover independent/static/dynamic cases, all seven factor types,
separate entity aggregation, common streams, HullWhite rate transformations,
correlation identity/tolerance preservation, custom/shared-credit rejection, stale
calculator results, full input guards and complete/omitted attribution ladders.
Selected FX/credit/recovery h/h2 differences must be <1e-4*max(1,abs(derivative));
selected collateral stability uses 1e-10. Component/attribution targets use explicit
absolute tolerances (commonly 1e-12 USD; smaller ordinary-scale identities use
1e-14/1e-15). Final new pytest.approx checks set rel=0: its default relative term
would otherwise loosen an absolute-only check. The full runs preceded this test-only
tightening; all affected tests were rerun on both platforms. Production code and
coverage configuration were unchanged after the full runs; no full rerun is implied.

The single suite warning is the existing Starlette/httpx TestClient deprecation.
Pip root warnings occurred only in build/disposable development installation;
production UID is 10001. No PostgreSQL skips were counted as live verification.
Python 3.14 and hosted CI were not executed. These timings are observed test durations,
not performance benchmarks or market/model accuracy claims. Early fixture Decimal
and test-comparison corrections were resolved before both full suites.

Verified commands include `python scripts/demo_xva.py`, `parallax-risk version`,
`python scripts/check_docs.py`, Ruff check/format, strict mypy, project pre-commit,
`python -m build`, `python -m coverage json` and `.\scripts\verify_phase7.ps1`.
The helper validates Compose, starts only the isolated stack, checks runtime/API/DB,
runs both full suites and calls `scripts/cleanup_docker.ps1 -Phase 7 -Apply` in
finally. An additional --rm labelled Linux session reran strict affected tolerances
and also called scoped cleanup in finally. Full inputs/results, coverage, replay,
package/file identities and detailed logs are retained under `artifacts/local/phase7/`.
There is no source commit in this workspace; none is fabricated.

## Assumptions and limitations

Unilateral additive adjustments are not a bilateral or recursive replication price.
Deterministic origin discounting omits stochastic discount/exposure covariance.
Default-grid alive collateral does not freeze calls or apply default-conditioned MPOR
and may bias loss near maturity. Static rank is non-adapted; dynamic hazard changes
marginal survival. Independent versus dependent estimates use different estimators,
so their total difference does not isolate dependence. No XVA/Greek confidence
interval, institution calibration approval or regulatory compliance is claimed.

Funding has no survival termination, hedge/treasury flows or recursive price. Supplied
spreads may economically overlap credit adjustments; automatic double-counting
avoidance is not claimed. External posted IM has no regulatory estimator/custody/
settlement and stays fixed in listed bumps. Credit spread is a credit-triangle
parameter sensitivity, not calibrated quote CS01. Only continuous CSA receive
threshold is bumped; discrete scheduling/eligibility changes have no central Greek.

Common streams do not remove default-bucket/exposure-kink noise. Recovery holds
baseline hazard fixed, but changes dynamic triangle intensity at fixed spread; no
universal dynamic sign is imposed. Arbitrary stochastic-rate FX still needs caller
consistency and is not made arbitrage-consistent by a Q label or rate bump alone.
Ordered allocation remains order dependent and residuals are never forced to zero.
Capital, validation lab, mutation/governance and production financial interfaces
remain later authorized phases; Phase 8 is NOT IMPLEMENTED.

## Documentation and decisions

Created nine Markdown files and updated 61 existing Markdown files, including
every canonical ADR, the register and affected project/navigation/domain/testing/
operations guides. Created methodology for unilateral credit/results, additive funding/external IM and
actual risk/attribution, a full workflow, first-run tutorial, this evidence report and
ADRs 0017–0019. Every canonical ADR receives a Phase 7 review; prior rows remain.
Material decisions are 0001, 0017, 0018, 0019 (four), extending inward architecture
and specifying new consumers rather than replacing accepted prior policies.

New glossary terms include unilateral CVA/DVA, signed XVA total, FCA/FBA/FVA/MVA,
excess funding spread, external segregated posted IM, default mass, central h/h2
stability, common random numbers, credit-triangle sensitivity, ordered attribution
and unexplained residual. The glossary, roadmap, workflow/domain diagrams, code
locations, reproducibility, testing/operations and navigation reflect actual scope.

Stale absent-XVA statements in README, code/domain/workflow/limits/methodology,
glossary and exposure tutorial were corrected; standalone portfolio/exposure scope
remains explicitly separate. No financial HTTP handler, persistent job, model
approval or regulatory IM is implied. Future capital/lab/governance/production
methodology, bilateral/default-conditioned closeout, regulatory IM, calibrated credit
quote risk and other unsupported sensitivities stay deferred; no empty future pages
were created. All 13 historical phase/maintenance/ADR records, notebooks, locks and cleanup/doc
validators remain unchanged by SHA-256 comparison to the retained 0.6.0 source archive.

## Docker cleanup and retained evidence

The helper's finally block removed only `parallax-risk-phase7-verification-api-1`,
`parallax-risk-phase7-verification-postgres-1`, its `default` test network and
`postgres_data` disposable volume. The separately labelled full-suite container
`parallax-risk-phase7-tests` and strict-tolerance container
`parallax-risk-phase7-tolerances` used --rm. Their disposable development files
left with the containers. Needed results were saved outside writable layers first.

Final exact-label inventories and cleanup preview show no Phase 7 containers,
networks or volumes remaining. All **35 unrelated container IDs/names/project labels**
match the before/final inventories. The normal Compose `parallax-risk` persistent
database was not selected. No other workload was stopped/deleted, no global
system/image/volume/builder prune, force image removal or arbitrary in-container
file deletion was used. Ambiguous ownership would be retained and reported.

Useful `parallax-risk:0.7.0` and 0.6.0/0.5.0/0.4.0/0.3.0/0.2.0/0.1.0 release/rollback
images, shared bases/layers/build cache, wheel/source releases, locked inputs and
local logs/replay/coverage/file hashes remain. Current image identity is
`sha256:becb25aaffb7389e5a34e0327e646da9cd69516d4cb5a66a80d9b5978dc09ee5`.
Actual ownership/image inventories are retained locally; ignored artifacts are not
persisted Git lineage. The unchanged cleanup script enforces exact project/workspace/
attachment ownership. [Cleanup policy](../operations/DOCKER.md).

## File manifest

Compared by SHA-256 with the retained 0.6.0 source archive: **22 files created,
69 updated, none removed**. Documentation: **9 Markdown files created, 61 updated**.
This measures source content, not Git commits; the workspace has no source commit.
All 13 historical evidence records are byte-identical. Full per-file hashes and
release integrity are retained locally; the final source archive matches workspace
source/docs after completion records are saved.

### Created

- `docs/decisions/0017-unilateral-credit-adjustments.md`
- `docs/decisions/0018-additive-funding-and-external-margin.md`
- `docs/decisions/0019-xva-common-stream-risk-attribution.md`
- `docs/methodology/FUNDING_MARGIN.md`
- `docs/methodology/XVA.md`
- `docs/methodology/XVA_SENSITIVITIES.md`
- `docs/tutorials/06-FIRST-XVA-RUN.md`
- `docs/validation/phase-7.md`
- `docs/workflows/XVA_WORKFLOW.md`
- `scripts/demo_xva.py`
- `scripts/verify_phase7.ps1`
- `src/parallax_risk/application/xva.py`
- `src/parallax_risk/application/xva_examples.py`
- `src/parallax_risk/application/xva_revaluation.py`
- `src/parallax_risk/domain/xva/__init__.py`
- `src/parallax_risk/domain/xva/calculators.py`
- `src/parallax_risk/domain/xva/contracts.py`
- `src/parallax_risk/domain/xva/risk.py`
- `tests/fixtures/xva.py`
- `tests/integration/test_xva_workflow.py`
- `tests/quantitative/test_xva.py`
- `tests/unit/test_xva_contracts.py`

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
- `docs/decisions/0014-conditional-market-paths.md`
- `docs/decisions/0015-credit-default-dependence.md`
- `docs/decisions/0016-exposure-statistics-and-cash-policy.md`
- `docs/decisions/README.md`
- `docs/methodology/CORRELATION.md`
- `docs/methodology/CREDIT_DEFAULT.md`
- `docs/methodology/EXPOSURE.md`
- `docs/methodology/INDEX.md`
- `docs/methodology/MARKET_DATA.md`
- `docs/methodology/MONTE_CARLO.md`
- `docs/methodology/MONTE_CARLO_STATISTICS.md`
- `docs/methodology/PORTFOLIO_COLLATERAL.md`
- `docs/methodology/PRICING.md`
- `docs/methodology/WRONG_WAY_RISK.md`
- `docs/methodology/deterministic-pricing.md`
- `docs/operations/CONFIGURATION.md`
- `docs/operations/DATABASE.md`
- `docs/operations/DOCKER.md`
- `docs/operations/LOCAL_SETUP.md`
- `docs/operations/OBSERVABILITY.md`
- `docs/operations/RELEASE.md`
- `docs/operations/TROUBLESHOOTING.md`
- `docs/testing/STRATEGY.md`
- `docs/tutorials/05-FIRST-EXPOSURE-RUN.md`
- `docs/validation/OVERVIEW.md`
- `docs/validation/SENSITIVITY.md`
- `pyproject.toml`
- `src/parallax_risk/__init__.py`
- `src/parallax_risk/api/schemas.py`
- `src/parallax_risk/cli/main.py`
- `tests/api/test_operations.py`
- `tests/integration/test_database_cli.py`

