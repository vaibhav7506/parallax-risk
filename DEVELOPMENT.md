# Developing Parallax Risk

Use Python 3.12–3.14 according to package metadata. Verified environments include
Windows 3.13.2 and Linux 3.12.14; 3.14 is unverified. Commands below run from the
repository root. On Windows, activation is optional; substitute `.venv\Scripts\python.exe`.

```sh
python -m venv .venv
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python -m ruff check .
python -m ruff format --check .
python -m mypy
python scripts/check_docs.py
python -m pytest
python -m build
python scripts/demo_deterministic.py
python scripts/demo_calibration.py
```

Activate the created environment before plain `python` commands: PowerShell
`.\.venv\Scripts\Activate.ps1`, or POSIX `. .venv/bin/activate`. The development lock
records the verified versions without package hashes; updates require revalidation.
Compatible dependency ranges are in `pyproject.toml`. Make targets are optional;
see [Makefile](Makefile), rather than assuming undocumented targets exist.

## Database and service

For Compose, copy `.env.example` to an untracked `.env`, replace all placeholders
and set an encoded PostgreSQL URL whose host is `postgres`. Library settings never
auto-load `.env`; Compose explicitly passes settings. For a host API/CLI, supply a
separate URL with the actual host database address.

```sh
docker compose config --quiet
docker compose up --build --wait
docker compose exec api parallax-risk check-db
docker compose down
python -m parallax_risk version
python -m parallax_risk config
python -m parallax_risk run-context
python -m uvicorn parallax_risk.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

There are no database tables or migration revisions. Alembic is installed for later
authorized persistence work; do not run or invent automatic migration commands.
`PARALLAX_TEST_DATABASE_URL` points pytest at an **isolated** PostgreSQL service.
Without it the PostgreSQL-marked test is skipped, which is not live integration evidence.

## Docker verification lifecycle

Use `scripts/compose.verify.yml` and a unique phase verification project. Ports
58000/55432 avoid this machine's unrelated port-8000 workload. Save useful outputs
before teardown. In PowerShell, wrap the verification session in `try/finally` and
call `scripts/cleanup_docker.ps1 -Phase 6 -Apply` in `finally`; increment only after
the next phase is authorized. Preview without `-Apply`. See
[Docker ownership and retention](docs/operations/DOCKER.md) for exact commands.

The active-phase helper `.\scripts\verify_phase6.ps1` builds the stack, verifies
HTTP/database/non-root runtime and runs real PostgreSQL Windows/Linux suites. It
uses ownership labels and always scoped cleanup; logs/artifacts remain under
`artifacts/local/phase6/`. SciPy stubs are development-only; runtime locks exclude them.

## Troubleshooting and contribution

Configuration/unknown variables fail explicitly, database errors are sanitized,
and unsupported instruments/curves/fixings are not substituted. See
[troubleshooting](docs/operations/TROUBLESHOOTING.md) and
[contributing](CONTRIBUTING.md). The full suite's existing Starlette/httpx adapter
deprecation warning is documented in phase evidence, not suppressed.

Phase 4 notebook execution uses nbformat/nbclient/ipykernel and Matplotlib from the
locked development environment. These packages do not enter the runtime lock/image.
Run `python scripts/demo_simulation.py`, `python scripts/benchmark_simulation.py`,
and `python scripts/execute_notebooks.py`. The executor uses a workspace-local kernel
spec and explicitly tears down its kernels; successful outputs and evidence are retained.
See [simulation tutorial](docs/tutorials/03-FIRST-SIMULATION-RUN.md).

Phase 5 reproduction: `python scripts/demo_portfolio.py`; quantitative policy lives in
`src/parallax_risk/domain/portfolio/`, orchestration in `src/parallax_risk/application/portfolio.py`.
Existing instruments/models and pinned dependencies are reused. Read the
[portfolio tutorial](docs/tutorials/04-FIRST-PORTFOLIO-RUN.md).

Phase 6 reproduction: `python scripts/demo_exposure.py`; read
[exposure workflow](docs/workflows/EXPOSURE_WORKFLOW.md) and
[credit assumptions](docs/methodology/CREDIT_DEFAULT.md). Full-scope verification
requires the live database suite, deliberate analytical/statistical tolerances and
>=95% branch-inclusive coverage. A skip is not live database evidence.
