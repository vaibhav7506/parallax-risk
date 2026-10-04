# Parallax Risk — Phase 2 completion evidence

**Status:** Complete. Stop here; Phase 3 requires the user's explicit `go`.
**Verification date:** 2026-10-01 (Asia/Calcutta).
**Release:** 0.2.0.

## Implemented

Frozen, versioned source-labelled market snapshots with canonical hashes and strict
Pydantic ingestion; discount, zero and simple index projection curves; declared
linear/log-linear interpolation and extrapolation; bounded deposit/par-swap bootstrap
with actual repricing diagnostics. Explicit fixed/floating cash flows, default-free
bonds, vanilla interest-rate swaps and deliverable FX forwards are priced through a
stateless discounting engine. Results include assumptions, model version, all input
digests and individual signed cash-flow contributions. Central finite-difference
zero-knot PV01/DV01 and direct-spot FX delta retain base/up/down evidence. An injected
pricing workflow correlates results and safe logs with the existing run context.

The deterministic demo uses labelled synthetic JSON and production library calls.
Architecture checks enforce inward dependencies; tests cover independent analytical
formulas, par instruments, FX parity, malformed/missing data, numerical failure,
negative rates, property invariants, regression guards and repeatable workflows.

## Requirement mapping

| Phase 2 requirement | Implementation and evidence |
|---|---|
| Snapshot/date/currencies/quotes | `domain/market/snapshot.py`, immutable observations, ingestion/replay tests |
| Rates/FX/volatility/credit | `observations.py`; explicit units, conventions and source/sample metadata |
| Immutable version/hash | Frozen nested tuples; canonical SHA-256; reordering/version/mutation tests |
| Malformed/missing data | Pydantic extra/finite/type checks; duplicate/date/currency validation; exact fixing/FX lookup |
| Discount/zero/forward curves | `term_structures.py`; explicit discount and index assignments |
| Interpolation/extrapolation | Typed strategy protocol, linear/log-linear, error/flat-zero policies |
| Bootstrap and diagnostics | Deposit/par-swap protocol, bounded bisection, final quote gate, curve sanity diagnostics |
| Fixed/floating abstraction | Explicit accrual/payment/fixing contracts and floating protocol |
| Bonds/swaps/FX forwards | Typed contracts, supplied schedules and direction/conventions |
| Pricing engine/result | `pricing/engine.py`, `results.py`; NPV/currency/date/version/assumptions and flow reconciliation |
| PV01/DV01/FX delta | Central finite differences with declared bump units/curve scope/signs; analytical derivative tests |
| Analytical benchmarks | Independent 50-digit Decimal exponential targets and hand-derived curve/instrument cases |
| Par swap/FX no-arbitrage | Single/dual-curve zero-PV swaps, spot-settlement-adjusted FX parity, direction reversal |
| Curve monotonicity/sanity | Positive anchor/DF checks; diagnostics; nonnegative-rate monotonicity properties; valid negative rates |
| Regression suite | Missing fixing/projection, payment cutoff, paid coupons, short deposit, extreme annuity |
| Conventions/tolerances | `docs/methodology/deterministic-pricing.md` and ADR-0005 |
| No stochastic simulation | No stochastic models, simulation or future-phase directories implemented |

## Observed checks

These are actual local observations. GitHub-hosted CI has not been run.

| Check | Actual result |
|---|---|
| Editable metadata and version | 0.2.0 installation; package/build/API/CLI consistency test passed |
| Dependency consistency | Host and production container `pip check`: no broken requirements |
| Ruff lint and formatting | All checks passed; project Python files formatted |
| Strict mypy | No issues in 46 production source files |
| Pre-commit | Ruff, formatting and mypy hooks passed on project Python files |
| Windows/Python 3.13.2 full pytest | **333 passed**, no skips, 12.94 seconds, live isolated PostgreSQL |
| Linux/Python 3.12.14 full pytest | **333 passed**, no skips, 16.44 seconds, installed production wheel and live isolated PostgreSQL |
| Statement + branch coverage | **99.07%** on both platforms: 1786 statements, 476 branches; gate >=95% |
| Import/dependency safety | All modules import without environment loading, engine/logger initialization or output; domain framework dependency checks passed |
| Synthetic workflow | Four prices, bootstrap and sensitivities computed; two subprocess runs yielded byte-identical JSON stdout |
| Packaging | Wheel and source archive built; wheel built from sdist; all 46 production Python modules and `py.typed` verified in wheel |
| Docker build | Final `parallax-risk:0.2.0` production image built on Linux/amd64 |
| Image identity | `sha256:1cb95e91d78b6f1a2893d918ec8256885295b156a876d1264e84395d4a44118d` |
| Compose startup | Isolated API and PostgreSQL services healthy with `up --wait` |
| Live HTTP | Health `ok`; readiness `ready`/database `connected`; version 0.2.0, phase 2 |
| Runtime identity | `id -u`: 10001 |
| CLI/database | Version reports Phase 2; `check-db` reports connected |
| Persistence scope | PostgreSQL public schema table count: 0 |

Both test suites emitted the existing Starlette/httpx TestClient deprecation warning.
It was retained, not suppressed. The disposable Linux test container installed the
locked development dependencies into its own layer; the production image retains
runtime dependencies only. The read-only bind-mounted workspace remained unchanged.

Verification used project `parallax-risk-phase2-verification`, loopback ports 58000
and 55432, and disposable test credentials. Only its containers, network and test
volume are removed after validation. The production image, distributions and local
virtual environment remain. Unrelated Docker workloads are untouched.

## Limitations and deferred work

- Pricing is checked binary64 with unrounded Decimal reporting; Money's exact-decimal
  arithmetic guarantee does not extend to quantitative valuation. Extreme overflow,
  underflow and NaN/Inf fail explicitly; the model does not claim arbitrary precision.
- Rates, dates, schedules, calendars, day counts, projection assignments and settlement
  must be supplied explicitly. Known fixings have no projection fallback. The daily
  snapshot cutoff does not implement intraday or vendor-specific freshness policies.
- Bootstrap supports valuation-date-start simple deposits and zero-spread, constant-
  notional single-curve par swaps with no payment lag. Heterogeneous basis calibration,
  official market conventions, convexity and market-quote sensitivity are absent.
- Bonds are default-free dirty PV; swaps contain coupon exchanges only. Optionality,
  default, accrued-interest/clean-price, ex-coupon and floating compounding are absent.
- FX is a direct quoted deliverable forward with explicit spot settlement and no
  cross-currency basis. Inverse/cross quotes and arbitrary reporting conversion are absent.
- PV01/DV01 means explicitly selected continuous-zero knot risk, with documented
  signs, fixed observed fixings and a caller-declared bump. It is not calibrated
  market-quote risk. FX delta uses an absolute direct-spot-rate bump.
- Volatility and credit spreads are observations only. Stochastic models/calibration
  begin in Phase 3; simulation, exposure, portfolios/netting/CSA, XVA, capital, model
  validation lab, mutation/adversarial search and governance remain in later phases.
- Financial API/CLI workflows, authentication and performance/scalable compute are
  deferred to Phase 12. Existing API/CLI remain operational endpoints/commands.
- Python 3.14 is allowed by metadata but was not tested here. Hosted CI 3.12/3.13 is
  configured but not claimed as executed. Dependency locks have exact versions but
  no hashes; base-image release tags do not guarantee immutable rebuilds.
- No live market data, fabricated external benchmark or regulatory compliance is claimed.

## Created files

The Phase 1 report remains historical evidence. Ignored environments, caches,
coverage outputs and distributions are excluded from this source manifest.

- `data/sample/phase2_market.json`
- `docs/adr/0005-deterministic-curves-and-pricing.md`
- `docs/methodology/deterministic-pricing.md`
- `docs/validation/phase-2.md`
- `scripts/demo_deterministic.py`
- `src/parallax_risk/application/market_data.py`
- `src/parallax_risk/application/pricing.py`
- `src/parallax_risk/common/canonical.py`
- `src/parallax_risk/domain/__init__.py`
- `src/parallax_risk/domain/_validation.py`
- `src/parallax_risk/domain/instruments/__init__.py`
- `src/parallax_risk/domain/instruments/cashflows.py`
- `src/parallax_risk/domain/instruments/fx/__init__.py`
- `src/parallax_risk/domain/instruments/fx/contracts.py`
- `src/parallax_risk/domain/instruments/rates/__init__.py`
- `src/parallax_risk/domain/instruments/rates/contracts.py`
- `src/parallax_risk/domain/market/__init__.py`
- `src/parallax_risk/domain/market/curves/__init__.py`
- `src/parallax_risk/domain/market/curves/bootstrap.py`
- `src/parallax_risk/domain/market/curves/diagnostics.py`
- `src/parallax_risk/domain/market/curves/interpolation.py`
- `src/parallax_risk/domain/market/curves/term_structures.py`
- `src/parallax_risk/domain/market/observations.py`
- `src/parallax_risk/domain/market/snapshot.py`
- `src/parallax_risk/domain/pricing/__init__.py`
- `src/parallax_risk/domain/pricing/_numbers.py`
- `src/parallax_risk/domain/pricing/engine.py`
- `src/parallax_risk/domain/pricing/results.py`
- `src/parallax_risk/domain/pricing/sensitivities.py`
- `tests/__init__.py`
- `tests/fixtures/__init__.py`
- `tests/fixtures/deterministic.py`
- `tests/integration/test_deterministic_workflow.py`
- `tests/property/test_deterministic_invariants.py`
- `tests/quantitative/test_deterministic_pricing.py`
- `tests/regression/test_deterministic_guards.py`
- `tests/regression/test_numerical_range.py`
- `tests/unit/test_curves_bootstrap.py`
- `tests/unit/test_market_snapshots.py`
- `tests/unit/test_pricing_contracts.py`

## Modified files

- `.github/workflows/ci.yml` — generic quality workflow title and current image version
- `Makefile` — current image tag
- `README.md` — Phase 2 scope, usage, precision and evidence
- `docker-compose.yml` — current image version
- `docs/architecture/foundation.md` — implemented domain/application boundaries
- `docs/methodology/primitives.md` — distinguish primitive helpers from Phase 2 valuation
- `pyproject.toml` — release version 0.2.0
- `src/parallax_risk/__init__.py` — matching package version
- `src/parallax_risk/api/schemas.py` — current phase metadata
- `src/parallax_risk/cli/main.py` — current phase metadata and operational scope
- `src/parallax_risk/common/errors.py` — explicit market/curve/bootstrap/pricing errors
- `src/parallax_risk/common/identifiers.py` — typed snapshot/version/quote/curve identifiers
- `tests/api/test_operations.py` — current phase metadata assertions
- `tests/integration/test_architecture.py` — enforce domain dependency direction
- `tests/integration/test_database_cli.py` — current release expectation

No new dependencies or future-phase scaffolding were introduced.
