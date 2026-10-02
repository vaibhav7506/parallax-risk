# Parallax Risk — Phase 1 completion evidence

**Status:** Complete. Stop here; Phase 2 requires the user's explicit `go`.
**Verification date:** 2026-10-01 (Asia/Calcutta).

## Implemented

A typed src-layout foundation with immutable nominal IDs, exact decimal Money,
explicit currency/date/calendar/day-count/compounding conventions and numerical
tolerances. Pydantic boundary configuration rejects invalid/unknown settings and
redacts credentials. Immutable run contexts record ID, UTC time, seed and a
canonical configuration digest. Structured loggers are instance-local and carry
run correlation without raw financial inputs. API/CLI factories compose a lazy,
bounded PostgreSQL connectivity adapter and own resource cleanup. Architecture
documentation and four ADRs explain layer, persistence and reproducibility choices.

Only operational endpoints/commands exist. No pricing, XVA, financial API,
governance tables or future-phase implementations have been added.

## Requirement mapping

| Phase 1 requirement | Implementation / evidence |
|---|---|
| 1. src scaffolding | `src/parallax_risk`, only implemented directories |
| 2. Controlled dependencies | `pyproject.toml`, runtime/dev exact-version snapshots |
| 3. Quality configuration | Ruff, strict mypy, pytest, branch coverage >=95%, pre-commit |
| 4. Structured logging | `common/logging.py`; JSON, instance-local configuration |
| 5. Configuration | `application/config.py`; immutable Pydantic settings, explicit loading |
| 6. Typed identifiers | `common/identifiers.py`; all seven named ID types |
| 7. Financial primitives | Currency, Decimal Money, dates/UTC, calendar port, day counts, compounding |
| 8. Error hierarchy | `common/errors.py`; domain, convention, numerical, config, infrastructure errors |
| 9. Numerical tolerances | `common/math.py`, boundary tolerance settings, documented units |
| 10. Deterministic context | `application/context.py`; ID/time/seed/hash injection and replay tests |
| 11. Architecture | `docs/architecture/foundation.md`, dependency-direction tests |
| 12. ADRs | Four records in `docs/adr/` |
| 13. Basic FastAPI | `/health`, `/ready`, `/version`; live container requests verified |
| 14. Dockerfile | Multi-stage Python 3.12 image, non-root UID 10001 |
| 15. Compose baseline | API + PostgreSQL 17, DB health ordering, internal DB network/volume |
| 16. CI | Install/lint/types/tests/build and live service/container jobs configured |
| 17. PostgreSQL abstraction | Application protocol + SQLAlchemy adapter, SELECT 1 only |
| 18. CLI | version, config, run-context, check-db; console/module invocation tested |
| 19. Version metadata | 0.1.0 package/build/API/CLI consistency tests |
| 20. Primitive/config tests | Formula benchmarks, rejection cases, property invariants, hash/replay contracts |

## Observed checks

These are actual local observations; the GitHub-hosted workflow has not been run.

| Check | Actual result |
|---|---|
| Editable installation | Passed in fresh project `.venv`, Python 3.13.2 |
| Dependency consistency | `pip check`: no broken requirements, host and container |
| Ruff lint | All checks passed |
| Ruff formatting | All checked project files already formatted |
| Strict mypy | No issues in 22 production source files |
| Pre-commit | Ruff, formatting and mypy hooks passed on all project Python files |
| Full pytest with real PostgreSQL | **141 passed**, no skips, 14.16 seconds |
| Statement + branch coverage | **99.84%**; 507 statements, 118 branches, one unmeasured entry-module import |
| Import safety | Isolated subprocess imports all modules without settings/engine/logger initialization |
| Python distribution | Wheel and source archive built successfully, including wheel built from sdist |
| Docker build | `parallax-risk:0.1.0` built on Linux/amd64, Python 3.12 |
| Image identity | `sha256:57116da79c97ee84aff692b564eb74a131e46a64ae3185f77058d2bbc842cf55` |
| Container user | `id -u` returned 10001 |
| Compose startup | Test project API and PostgreSQL both healthy with `up --wait` |
| HTTP health | `{"status":"ok"}` |
| HTTP readiness | `{"status":"ready","database":"connected"}` |
| HTTP version | Parallax Risk, 0.1.0, Phase 1 |
| Container CLI database query | `{"database":"connected"}` |
| Application database tables | Public-schema table count = 0 |

The test run emitted two non-failing warnings: the installed Starlette version
deprecates its httpx TestClient adapter, and this host's restricted pytest cache
directory rejected a cache write during the elevated PostgreSQL run. Neither
warning changes assertions, coverage or DB checks; no warnings were suppressed.
The legacy adapter remains usable in this locked environment and needs review
on a future dependency update.

The continuous-compounding benchmark initially contained a transcribed expected
value error. The test detected it; expected exp(0.1) was corrected against a
50-digit Decimal calculation. No tolerance was widened and no implementation
was changed to satisfy the erroneous benchmark.

Port 8000 was already allocated by another workload. Verification used a
test-only Compose override with API port 58000 and PostgreSQL port 55432, both
bound to loopback. The normal Compose baseline remains API port 8000 with no
published DB port. Verification containers/network and their disposable test
volume are removed after validation; the built image and local venv remain.

## Limitations and deferred work

- Currency is a declared ten-code subset; minor-unit/settlement rounding and FX
  conversion are absent. Money arithmetic traps precision loss beyond 34 digits.
- Holiday sets are supplied by callers. No official exchange calendars, holiday
  feed, coupon schedule or business-center convention is implied.
- Supported day counts are ACT/360, ACT/365F, ACT/ACT ISDA and European 30E/360.
  US 30/360, ACT/ACT ICMA and 30E/360 ISDA are unsupported.
- The configuration hash excludes secrets. Full portfolio/market/model/calibration/
  CSA/source/sequence/environment lineage awaits its specified later phases.
- PostgreSQL configuration supports single-host psycopg URLs without query options.
  SQLite is not a production fallback. Alembic is declared, with no tables or
  migrations implemented before the governance phase.
- Authentication, authorization, financial endpoints and broader service security
  belong to Phase 12. This operational baseline is intended for local use.
- Python 3.13.2 was used for local tests; Python 3.12 was verified through the
  container build/service run. Hosted CI 3.12/3.13 tests are configured but not
  claimed as executed. Python 3.14 is permitted by metadata but unverified here.
- No pricing, stochastic modelling, simulation, portfolios/netting/CSA, exposure,
  credit, XVA, capital, validation lab, mutation/adversarial search, governance or
  production financial workflows exist. Each remains in its designated phase.
- Dependency locks record exact installed versions without hashes; cross-platform
  updates require revalidation. Base images are controlled release tags, not
  immutable whole-environment rebuild guarantees.

## Created/modified file manifest

The workspace was empty apart from `.git`; all files below were created in Phase 1.
Ignored virtual environments, caches, coverage output and build artifacts are not
source files. Local `dist/` contains the 0.1.0 wheel and source archive.

- `.dockerignore`
- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.pre-commit-config.yaml`
- `Dockerfile`
- `LICENSE`
- `Makefile`
- `README.md`
- `docker-compose.yml`
- `docs/adr/0001-clean-architecture.md`
- `docs/adr/0002-quantitative-domain-separation.md`
- `docs/adr/0003-persistence-boundaries.md`
- `docs/adr/0004-reproducibility.md`
- `docs/architecture/foundation.md`
- `docs/methodology/primitives.md`
- `docs/validation/phase-1.md`
- `pyproject.toml`
- `requirements-dev.lock`
- `requirements-runtime.lock`
- `scripts/compose.verify.yml`
- `scripts/lock_dependencies.py`
- `src/parallax_risk/__init__.py`
- `src/parallax_risk/__main__.py`
- `src/parallax_risk/api/__init__.py`
- `src/parallax_risk/api/app.py`
- `src/parallax_risk/api/schemas.py`
- `src/parallax_risk/application/__init__.py`
- `src/parallax_risk/application/config.py`
- `src/parallax_risk/application/context.py`
- `src/parallax_risk/application/ports.py`
- `src/parallax_risk/cli/__init__.py`
- `src/parallax_risk/cli/main.py`
- `src/parallax_risk/common/__init__.py`
- `src/parallax_risk/common/enums.py`
- `src/parallax_risk/common/errors.py`
- `src/parallax_risk/common/identifiers.py`
- `src/parallax_risk/common/logging.py`
- `src/parallax_risk/common/math.py`
- `src/parallax_risk/common/money.py`
- `src/parallax_risk/common/time.py`
- `src/parallax_risk/infrastructure/__init__.py`
- `src/parallax_risk/infrastructure/persistence/__init__.py`
- `src/parallax_risk/infrastructure/persistence/database.py`
- `src/parallax_risk/py.typed`
- `tests/api/test_operations.py`
- `tests/conftest.py`
- `tests/integration/test_architecture.py`
- `tests/integration/test_database_cli.py`
- `tests/property/test_invariants.py`
- `tests/unit/test_config_context_logging.py`
- `tests/unit/test_primitives.py`
