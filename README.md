# Parallax Risk

Quantitative counterparty credit risk, XVA and model validation platform.

**Current scope: Phase 2 — market data, curves and deterministic pricing.**
Immutable market snapshots, discount/zero/projection curves, deposit/par-swap
bootstrapping, cash flows, bonds, swaps, FX forwards and finite-difference
sensitivities are implemented. This repository makes no
regulatory-compliance claim. Implementation advances one phase at a time, only
after the user writes `go`.

## Install and check

Python 3.12–3.14 is supported by package metadata. Local verification uses the
available interpreter; CI checks Python 3.12 and 3.13. From the repository root:

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# POSIX shell: . .venv/bin/activate
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest
python -m build
python -m pre_commit install
```

Controlled compatible ranges live in `pyproject.toml`; generated dependency
locks record the verified environment. Use `pip install -r requirements-dev.lock`
then `pip install --no-deps -e .` to replay it. `make check` is an optional
convenience on machines with Make. No Make dependency is required on Windows.

## Operational commands

```sh
parallax-risk --help
parallax-risk version
parallax-risk config
parallax-risk run-context
parallax-risk check-db
python -m uvicorn parallax_risk.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

`/health` is process liveness. `/ready` returns 200 only after startup and a real
PostgreSQL `SELECT 1`; it returns 503 for missing/unavailable dependencies.
`/version` identifies Parallax Risk, release 0.2.0 and Phase 2. These endpoints do
not perform financial calculations. API and CLI imports perform no environment,
network, filesystem or logger initialization.

Settings load explicitly from `PARALLAX_` environment variables; library code
does not load `.env`. Environment choices are `development`, `test`, `production`.
Unknown application environment names fail explicitly instead of silently using
defaults; integer environment values require ASCII decimal digits.
Production requires an explicit PostgreSQL URL. To run with local PostgreSQL,
set `PARALLAX_DATABASE_URL` to a single-host
`postgresql+psycopg://user:password@host:5432/parallax_risk` URL, with URL-encoded
credentials. Supported timeout is 1–30 seconds; default is 5. URL query parameters
are unsupported. Credentials never appear in CLI configuration output.

`PARALLAX_DEFAULT_SEED` is uint64 (default 0). Foundation tolerances are
`PARALLAX_TOLERANCES__ABSOLUTE=1e-12` and
`PARALLAX_TOLERANCES__RELATIVE=1e-9`; these are dimensionless scalar checks,
not money, calibration or Monte Carlo acceptance thresholds.

## Containers and PostgreSQL

Copy `.env.example` to an untracked `.env` and replace **all** placeholders.
Compose passes database variables to the container explicitly. For this baseline
use URL-safe credentials, or provide a correctly URL-encoded application URL.

```sh
docker compose config --quiet
docker compose up --build --wait
docker compose exec api parallax-risk check-db
docker compose down
```

PostgreSQL is internal to the Compose network, with a persistent named volume.
API binds to loopback port 8000. The image runs as a non-root user. No tables are
created in the current scope. Do not remove the database volume unless its contents are no
longer needed. The PostgreSQL integration test uses only `SELECT 1` and requires
`PARALLAX_TEST_DATABASE_URL`; otherwise pytest explicitly skips it. CI supplies
a real isolated PostgreSQL service and additionally tests the container stack.

For local integration verification, `scripts/compose.verify.yml` uses loopback
API port 58000 and publishes the test database to loopback port 55432.
Use an isolated Compose project name,
disposable credentials and `PARALLAX_TEST_DATABASE_URL` pointing to that port.
The override is unnecessary for normal operation.

## Conventions, architecture and evidence

- [Architecture](docs/architecture/foundation.md)
- [Financial conventions and numerical limitations](docs/methodology/primitives.md)
- [Deterministic pricing, curves, signs and tolerances](docs/methodology/deterministic-pricing.md)
- [ADRs](docs/adr/0001-clean-architecture.md)
- [Phase 1 verification and file manifest](docs/validation/phase-1.md)
- [Phase 2 verification and file manifest](docs/validation/phase-2.md)

## Deterministic pricing example

```sh
python scripts/demo_deterministic.py
```

The example validates `data/sample/phase2_market.json` through the Pydantic
boundary, constructs explicit curves, prices four contracts, bootstraps a
deposit/par-swap curve, and computes bond PV01/DV01 and FX delta. Standard output
contains computed JSON results, cash-flow evidence, input hashes and fixed run
metadata; safe workflow logs go to standard error. Every observation is explicitly
labelled synthetic. These are hand-specified examples, not observed market prices.
The Python domain library is the Phase 2 financial interface; production financial
CLI/HTTP workflows belong to Phase 12.

Schedules, day counts, compounding, projection assignments, extrapolation and
sensitivity bumps must be explicit. Known floating fixings are required even on
the valuation date. Positive discounts may increase when rates are negative.
FX quotes are QUOTE/BASE with a declared settlement date. The pricing model uses
checked binary64 arithmetic and reports unrounded currency units in Decimal
Money; its computations do not inherit Money's exact-decimal arithmetic guarantee.
No simulation, stochastic calibration, exposure, XVA or capital model is present.

Decimal Money prohibits implicit currency conversion, float amounts and silent
rounding. Calendars use declared weekend/holiday sets, never assumed official
market holidays. Run contexts record ID, UTC timestamp, seed and canonical
nonsecret configuration hash; explicit ID/time injection supports metadata replay.
Pricing additionally records market, curve and instrument hashes, model version,
assumptions and each cash-flow contribution. Portfolio/calibration/governance
lineage belongs to later phases.
