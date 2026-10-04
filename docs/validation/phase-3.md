# Parallax Risk — Phase 3 implementation and verification

**Status:** Complete. **Release:** 0.3.0. Phase 4 remains NOT IMPLEMENTED;
stop and wait for the user's next `go`.

## Requirements and evidence

| Phase 3 requirement | Actual implementation / evidence |
|---|---|
| Vasicek, Hull–White, GBM, Heston | Immutable coefficients and supplied-shock transitions in `src/parallax_risk/domain/models/` |
| Drift/diffusion and discretization interfaces | StochasticProcess, ExactProcess, Discretization; Euler, exact supported transitions, reported Heston projected Euler |
| Discretization error | Documented regularity/order limits, projection bias, marginal-rate limitation; local refinement tests |
| Correlation validation/PSD/Cholesky | Strict structure/order/entries, explicit PSD roundoff/singular policy, reconstruction tests |
| Explicit requested/reported repair only | Separate requested=True eigenvalue clipping/rescaling report; no automatic caller |
| SciPy calibration/objectives/bounds | Application port and infrastructure TRF adapter; sourced Q-model bond/bond-call/call objectives |
| Run identity/hashes/parameters/errors | Immutable CalibrationResult and CalibrationRunResult with raw/scaled metrics, bounds, status, evaluation counts |
| Uncertainty metadata | Jacobian SVD rank/condition/degrees of freedom; local covariance or explicit absence reason |
| Rate calibration examples | Ten Vasicek discounts and six Hull–White bond calls; known synthetic truth |
| Heston calibration | Twelve European calls, actual five-parameter recovery |
| Recovery/stability/failures/boundaries | Independent Gaussian-integral/ODE checks; perturbation/replay, budget/active-bound/identification/invalid data tests |
| No XVA/Phase 4 pre-build | No RNG, paths, time grid, batching, exposure or XVA engine introduced |

The preliminary Windows run had 474 passed, one explicitly skipped PostgreSQL test,
99.01% coverage; that run is not live database evidence. Final checks are recorded
below after execution. No CI execution or real-market calibration is claimed.

## Verification record

| Check | Actual result |
|---|---|
| Windows Python 3.13.2, isolated PostgreSQL | **483 passed**, no skips, 47.09 seconds; one existing Starlette/httpx deprecation warning |
| Linux Python 3.12.14, installed production wheel, isolated PostgreSQL | **483 passed**, no skips, 55.47 seconds; same existing adapter warning |
| Branch-inclusive coverage | **99.01%** on both platforms; 2,719 statements and 630 branches, >=95% gate passed |
| Ruff/format | All checks passed; 162 source/test/script/Markdown files already formatted |
| Strict mypy | No issues in 60 production modules; SciPy development stubs installed |
| Pre-commit | Ruff, formatting and mypy passed for all production/test/script Python files |
| Dependency consistency | pip check: no broken requirements; runtime lock excludes SciPy typing dependencies |
| Documentation | 72 Markdown files, 9 canonical ADRs, 398 concrete code references; local links, reachability and all completed-phase histories passed |
| Packaging | 0.3.0 wheel and sdist built; package/build/API/CLI version consistency tested |
| Docker build/runtime | Linux/amd64 0.3.0 production image built; normal API UID **10001** |
| HTTP/database | health ok, ready/database connected; version Parallax Risk / 0.3.0 / phase 3; container check-db connected |
| Examples | Both sample workflows pass integration execution; new calibration demo and documented process snippets run |
| Cleanup | Each verification session completed ownership-checked finally teardown; --rm Linux test container removed its temporary dev installation/files |

The initial container session passed 479 tests/98.75%; final checks add four very
short-maturity Riccati-ODE cases and use a fresh project-local Windows pytest cache.
The initial cache-write warning is retained in its log; it does not recur in final
verification. Logs are under `artifacts/local/phase3/`, with initial evidence in
`initial-verification/`. Hosted GitHub Actions and Python 3.14 were not executed.

Computed synthetic recovery (parameter order is documented per objective):

| Model | Fitted parameters | Raw RMSE / units |
|---|---|---|
| Vasicek | (.350000000494, .0549999999331, .0249999997208) | 2.6241e-12 discount-factor units |
| Hull–White | (.180000000218, .0120000000069) | 2.4277e-12 nominal fractions |
| Heston | (1.5, .045, .35, -.65, .035), within displayed precision | 1.0049e-14 currency units per underlying unit |

Synthetic recovery is internal consistency evidence. Independent Gaussian-integral
and Riccati-ODE checks are distinct mathematical validation; no external pricer,
real-market performance, confidence calibration or global optimum is claimed.

## Docker removal and retention

Removed from each exact `parallax-risk-phase3-verification` session: its api/postgres
containers, default network and disposable postgres_data volume. The named Linux
test container used --rm; its pip/dev/cache/temporary coverage files disappeared.
Before/after non-Parallax container ID/name/project inventories match exactly.
Final label-based inventory confirms no remaining Phase 3 verification resources.
Normal Compose services/data and other projects were not selected.

Retained useful release/rollback images: 0.3.0, 0.2.0 and 0.1.0; shared base layers/
build cache and host evidence/archives remain. Final 0.3.0 image identity:
`sha256:d97f873367ac89fe7a9648d74551b942e658800fbd2342877b7e3c263bdb949e`.
The replaced initial Phase 3 image ID was inspected and already absent; no manual
image deletion or global prune was performed. The repository's historical reports
retain their original results.

## Quantitative assumptions and limitations

- Risk-neutral rate/Heston constant coefficients; GBM drift/measure caller specified.
- Times are explicit year fractions; negative rates are allowed; Hull–White smooth
  initial forwards are linear, not guessed from an interpolated market curve.
- Exact rate transitions are marginal, excluding joint integrated-rate discounting.
- Heston projected Euler has boundary bias and reports each variance projection.
- Calls are European, continuous deterministic r/q, premiums per one underlying unit.
  Quadrature error is estimated, not a rigorous bound; no prices are silently clipped.
- Local bounded fitting has no global-minimum, real-market or model-approval claim.
  Covariance is local iid-scaled-residual inference, absent for invalid identification.
- Calibration data are distinct from snapshot raw vol quotes, explicitly synthetic
  in examples. No persistence, multistart/bootstrap, uncertainty propagation or API job.
- Correlation repair is opt-in with retained evidence, not a nearest-matrix guarantee.
- Phase 4 and later random/path/exposure/XVA/governance features remain deferred.

See [methodology index](../methodology/INDEX.md) and [limitations](../LIMITATIONS.md).

## Files created

- `src/parallax_risk/domain/models/__init__.py`, `base.py`, `rates.py`, `assets.py`,
  `discretization.py`, `correlation.py`, `heston_pricing.py` in that package.
- `src/parallax_risk/domain/calibration/__init__.py`, `contracts.py`, `problems.py`.
- `src/parallax_risk/application/calibration.py`, `calibration_inputs.py`.
- `src/parallax_risk/infrastructure/calibration/__init__.py`, `scipy_solver.py`.
- `tests/fixtures/stochastic.py`, `tests/quantitative/test_stochastic_models.py`,
  `tests/quantitative/test_calibration.py`, `tests/unit/test_model_guards.py`,
  `tests/unit/test_correlation.py`, `tests/unit/test_calibration_guards.py`,
  `tests/property/test_model_invariants.py`, `tests/integration/test_calibration_workflow.py`.
- `data/sample/phase3_calibration.json`, `scripts/demo_calibration.py`,
  `scripts/verify_phase3.ps1` (real database/container checks and finally cleanup).
- Seven methodology pages: STOCHASTIC_PROCESSES, VASICEK, HULL_WHITE, GBM,
  HESTON, CORRELATION, CALIBRATION; workflow, tutorial and this evidence report.
- ADRs [0008](../decisions/0008-stochastic-models-and-discretization.md) and
  [0009](../decisions/0009-bounded-calibration-and-uncertainty.md).

## Files modified

Common errors/identifiers; package/project/API/CLI release metadata; CLI/API version
tests; Compose/Makefile image tag; development dependencies and lockfiles; `.gitignore`.
All canonical ADR histories/index, affected root/index/code/domain/workflow/glossary/
limitations/reproduction/methodology/architecture/testing/operations/API guides.
Phase 1/2 historical reports and historical ADRs remain unchanged.

## DOCUMENTATION UPDATE

Created: seven methodology pages, calibration workflow/tutorial, Phase 3 report and
two ADRs. Updated: affected current guides, every canonical ADR history and decision
ledger. ADR 0005 moves from proposed to implemented; 0008/0009 are new. New terms:
OU loading, risk-neutral measure, drift/diffusion, exact marginal transition, projected
Euler, Feller margin, characteristic function, Fourier inversion, PSD/Cholesky,
scaled residual, Jacobian rank, active bound, local covariance. Assumptions/limits above.
Architecture/workflow documentation changed: yes. Commands and final counts are
recorded above. Commands verified: lint/format/mypy, docs checker, pre-commit,
pip check, pytest on both platforms, build, demo_calibration, both process examples,
version, Compose config/start, health/ready/version/check-db, scoped cleanup.
Corrected stale Phase 3/calibration availability claims and security/contributor scope;
kept deterministic model version 0.2.0 distinct from release 0.3.0. Deferred detailed
Monte Carlo/exposure/XVA/capital/governance/performance documents remain uncreated.

## Exact phase file manifest

The runtime dependency lock was reviewed/regenerated without changing its package
versions. Historical phase reports/ADRs retain their original outcomes. Generated
local logs, coverage and release archives are retained outside the source manifest.

### Created production modules

- `src/parallax_risk/domain/models/__init__.py`
- `src/parallax_risk/domain/models/base.py`
- `src/parallax_risk/domain/models/rates.py`
- `src/parallax_risk/domain/models/assets.py`
- `src/parallax_risk/domain/models/discretization.py`
- `src/parallax_risk/domain/models/correlation.py`
- `src/parallax_risk/domain/models/heston_pricing.py`
- `src/parallax_risk/domain/calibration/__init__.py`
- `src/parallax_risk/domain/calibration/contracts.py`
- `src/parallax_risk/domain/calibration/problems.py`
- `src/parallax_risk/application/calibration.py`
- `src/parallax_risk/application/calibration_inputs.py`
- `src/parallax_risk/infrastructure/calibration/__init__.py`
- `src/parallax_risk/infrastructure/calibration/scipy_solver.py`

### Created tests/fixtures

- `tests/fixtures/stochastic.py`
- `tests/quantitative/test_stochastic_models.py`
- `tests/quantitative/test_calibration.py`
- `tests/unit/test_model_guards.py`
- `tests/unit/test_correlation.py`
- `tests/unit/test_calibration_guards.py`
- `tests/property/test_model_invariants.py`
- `tests/integration/test_calibration_workflow.py`

### Created sample/operation scripts

- `data/sample/phase3_calibration.json`
- `scripts/demo_calibration.py`
- `scripts/verify_phase3.ps1`

### Created documentation

- `docs/methodology/STOCHASTIC_PROCESSES.md`
- `docs/methodology/VASICEK.md`
- `docs/methodology/HULL_WHITE.md`
- `docs/methodology/GBM.md`
- `docs/methodology/HESTON.md`
- `docs/methodology/CORRELATION.md`
- `docs/methodology/CALIBRATION.md`
- `docs/workflows/CALIBRATION_WORKFLOW.md`
- `docs/tutorials/02-FIRST-CALIBRATION-RUN.md`
- `docs/validation/phase-3.md`
- `docs/decisions/0008-stochastic-models-and-discretization.md`
- `docs/decisions/0009-bounded-calibration-and-uncertainty.md`

### Updated code/build/configuration

- `src/parallax_risk/common/errors.py`
- `src/parallax_risk/common/identifiers.py`
- `src/parallax_risk/__init__.py`
- `src/parallax_risk/api/schemas.py`
- `src/parallax_risk/cli/main.py`
- `tests/api/test_operations.py`
- `tests/integration/test_database_cli.py`
- `pyproject.toml`
- `requirements-dev.lock`
- `Makefile`
- `docker-compose.yml`
- `.gitignore`
- `.dockerignore`

### Updated documentation

- `README.md`
- `AGENTS.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `DEVELOPMENT.md`
- `docs/INDEX.md`
- `docs/CODEBASE_GUIDE.md`
- `docs/WORKFLOW.md`
- `docs/DOMAIN_MODEL.md`
- `docs/GLOSSARY.md`
- `docs/LIMITATIONS.md`
- `docs/REPRODUCIBILITY.md`
- `docs/architecture/OVERVIEW.md`
- `docs/architecture/COMPONENTS.md`
- `docs/architecture/DATA_FLOW.md`
- `docs/architecture/DEPENDENCY_RULES.md`
- `docs/architecture/foundation.md`
- `docs/methodology/INDEX.md`
- `docs/methodology/PRICING.md`
- `docs/methodology/MARKET_DATA.md`
- `docs/methodology/deterministic-pricing.md`
- `docs/methodology/primitives.md`
- `docs/validation/OVERVIEW.md`
- `docs/testing/STRATEGY.md`
- `docs/operations/DOCKER.md`
- `docs/operations/RELEASE.md`
- `docs/operations/TROUBLESHOOTING.md`
- `docs/api/ENDPOINTS.md`
- `docs/decisions/0001-clean-architecture.md`
- `docs/decisions/0002-money-representation.md`
- `docs/decisions/0003-immutable-market-snapshots.md`
- `docs/decisions/0004-random-sequence-reproducibility.md`
- `docs/decisions/0005-correlation-validation.md`
- `docs/decisions/0006-persistence-boundaries.md`
- `docs/decisions/0007-deterministic-curves-and-pricing.md`
- `docs/decisions/README.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `docs/operations/LOCAL_SETUP.md`
- `docs/validation/BENCHMARKING.md`

Documentation totals: **12 created; 40 updated**.
