# Parallax Risk

Quantitative counterparty credit risk, XVA and model validation platform.

Banks exchange derivative payments with counterparties. A derivative can become
valuable to the bank before the counterparty defaults, leaving positive value at
risk. Exposure and valuation-adjustment models estimate that risk; the models can
also be wrong. Parallax Risk is intended to calculate and challenge those models.
The implemented foundation covers deterministic pricing, stochastic model primitives
and calibration; future credit
risk and model-validation workflows remain in their authorized phases.

Educational/research implementation. Not production trading/risk software. Not
regulatory certification.

**Current scope: Phase 3 — stochastic market models and calibration.**
Immutable market snapshots, discount/zero/projection curves, deposit/par-swap
bootstrapping, cash flows, bonds, swaps, FX forwards and finite-difference
sensitivities are implemented. Phase 3 adds Vasicek, Hull–White, GBM, Heston,
exact/Euler step strategies, correlation validation and bounded instrument calibration.
This repository makes no
regulatory-compliance claim. Implementation advances one phase at a time, only
after the user writes `go`.

```mermaid
flowchart LR
    API[Operational API / CLI] --> APP[Application boundaries and ports]
    APP --> DOMAIN[Market, curves, contracts, pricing and model objectives]
    DOMAIN --> CORE[Typed common primitives]
    DB[PostgreSQL adapter] --> APP
    SOLVER[SciPy calibration adapter] --> APP
```

Python 3.12+, Pydantic v2, FastAPI, SQLAlchemy/PostgreSQL and structlog provide
typed boundaries and operations. NumPy handles matrix validation/SVD; SciPy supplies
quadrature and optimization; deterministic core arithmetic uses the standard library. Ruff, mypy,
pytest/Hypothesis, coverage, Docker/Compose and GitHub Actions support verification.

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
python scripts/check_docs.py
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
`/version` identifies Parallax Risk, release 0.3.0 and Phase 3. These endpoints do
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

- [Documentation homepage and learning paths](docs/INDEX.md)
- [Codebase guide and change locations](docs/CODEBASE_GUIDE.md)
- [Development](DEVELOPMENT.md), [contributing](CONTRIBUTING.md), [security](SECURITY.md)
- [Roadmap](ROADMAP.md) and [phase changelog](CHANGELOG.md)
- [Architecture](docs/architecture/foundation.md)
- [Financial conventions and numerical limitations](docs/methodology/primitives.md)
- [Deterministic pricing, curves, signs and tolerances](docs/methodology/deterministic-pricing.md)
- [Decision index and per-phase changes](docs/decisions/README.md)
- [Phase 1 verification and file manifest](docs/validation/phase-1.md)
- [Phase 2 verification and file manifest](docs/validation/phase-2.md)
- [Phase 3 verification and file manifest](docs/validation/phase-3.md)
- [Project-scoped Docker cleanup and retention](docs/operations/DOCKER.md)

After every phase, review every canonical ADR and append its phase history, update
the decision ledger/changelog and affected guides, validate local links, and clean
only disposable Parallax Risk verification resources. Keep useful release images
and production data. The [agent rules](AGENTS.md) make this part of phase acceptance.

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
Random/path simulation, exposure, XVA and capital models remain NOT IMPLEMENTED.

Decimal Money prohibits implicit currency conversion, float amounts and silent
rounding. Calendars use declared weekend/holiday sets, never assumed official
market holidays. Run contexts record ID, UTC timestamp, seed and canonical
nonsecret configuration hash; explicit ID/time injection supports metadata replay.
Pricing additionally records market, curve and instrument hashes, model version,
assumptions and each cash-flow contribution. Calibration records its own ID,
input/settings hashes, bounds, fitted parameters and residuals. Portfolio/governance
and automatic code/environment lineage remain later-phase work.

## Stochastic models and calibration example

```sh
python scripts/demo_calibration.py
```

Strict inputs in `data/sample/phase3_calibration.json` feed three actual SciPy fits:
Vasicek discount bonds, Hull–White bond options and Heston European calls. Data are
explicitly generated and labelled synthetic. Results report convergence/failure,
signed residuals, raw/scaled RMSE, parameter bounds, Jacobian identification and
local covariance or a reason for its absence. See the
[calibration tutorial](docs/tutorials/02-FIRST-CALIBRATION-RUN.md) and
[methodology](docs/methodology/CALIBRATION.md).

Model steps consume caller-supplied independent standardized shocks; they generate
no random numbers or paths. Hull–White uses a declared linear instantaneous forward
curve. Heston projected Euler reports variance projection; its European call pricer
reports quadrature estimates and rejects numerical failure. Correlation validation
never repairs inputs automatically; a separate opt-in repair retains full evidence.
These are research models with documented limitations, not real-market validation.
The existing deterministic-discounting model remains version 0.2.0 within release 0.3.0.
