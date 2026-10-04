# Parallax Risk contributor and agent rules

Parallax Risk is a research platform for quantitative counterparty credit risk,
XVA and model validation. Document the actual repository so a new engineer can
understand the financial reasoning, locate the code and reproduce results.

## Current phase

- Current implementation phase: **3 — complete**; release 0.3.0.
- Completed implementation phases: **1, 2, 3**.
- Next implementation phase: **4 — Monte Carlo research engine, NOT IMPLEMENTED**.
- Documentation maintenance between phases does not advance the implementation phase.
- Implement exactly one numbered phase when the user writes `go`; complete its
  code, applicable tests, documentation and cleanup, then stop. Never pre-build the next phase.

## Non-negotiable rules

Financial correctness takes priority over speed. Never fabricate market data,
benchmarks, test outcomes, accuracy, performance or regulatory compliance. Label
synthetic data and future work. Reject invalid inputs without silent repair or
fallback. State units, currency, signs, date/compounding conventions and numerical
tolerances. Keep quantitative logic outside API handlers and persistence adapters.
Do not bypass required checks or remove limitations to improve appearances.

## Architecture and style

Use typed src-layout Python and immutable domain values. `domain` depends on
`common`, never FastAPI, Pydantic, SQLAlchemy or application code. `application`
owns validated boundaries and injected workflows; `infrastructure` implements
application ports; `api` and `cli` compose dependencies and own resource lifetimes.
`common` does not depend on domain/application. No import-time settings, engines,
network access, global RNGs or global logger configuration. Keep functions focused
and failures explicit. Decimal Money arithmetic and binary64 pricing have different
precision contracts; never imply exact-decimal valuation.

## Phase documentation acceptance

Inspect all changes and update affected guides in the same phase. Review README,
this file, ROADMAP, CHANGELOG, docs/INDEX, CODEBASE_GUIDE, WORKFLOW, DOMAIN_MODEL,
GLOSSARY, LIMITATIONS, reproducibility, methodology, testing and operations.
Create relevant documents only when they explain actual functionality or an
explicit user-requested proposed decision. Do not create empty future model pages.

`docs/decisions/README.md` is the canonical decision index. After **every phase**:

1. Update its phase ledger and affected decision IDs/counts.
2. Review **every** canonical ADR and append a phase-history row, including
   "reviewed; no change" or "not applicable; NOT IMPLEMENTED" when appropriate.
3. Preserve prior history. A material replacement marks the old ADR superseded
   and creates a new numbered ADR; never reuse an ID or rewrite away a decision.
4. Record additions, behavioral changes, verification, assumptions, limitations,
   file manifest and Docker resources retained/removed in the phase report.
5. Run `python scripts/check_docs.py`; check code references and changed commands.

At phase completion report documentation created/updated, ADRs, new terminology,
assumptions/limitations, architecture/workflow changes, commands verified,
inconsistencies corrected and deferred documents. Historical phase reports and
`docs/adr` records remain evidence; do not retroactively relabel their test results.

## Tests and Docker cleanup

Run Ruff, formatting, strict mypy and tests applicable to code changes; the full
quantitative phase suite requires deliberate tolerances and >=95% branch-inclusive
coverage. A skipped PostgreSQL test is not a live database verification. Record
actual environments and results. Documentation-only updates need link/reference and
command checks; do not claim the earlier 333-test run was newly executed.

After a Docker verification session, remove its disposable containers (which also
removes their temporary writable files), test networks and disposable test volumes.
Use `scripts/cleanup_docker.ps1 -Phase N -Apply` in a `finally` block after saving
needed results. The default is an inventory preview. The script scopes cleanup to
`parallax-risk-phaseN-verification` and checks ownership. Test-run containers use
`--rm` and explicit Parallax Risk verification labels. Keep useful release/rollback
images, shared base layers/build cache, production data and artifacts needed later.
Do not use global Docker/system/image/volume/builder prune, force-remove images,
delete arbitrary files inside containers, or stop/delete other projects' resources.
Ambiguous ownership means retain and report. Never delete the normal Compose
`parallax-risk` persistent database during test cleanup.

## Navigation

- Core Money: `src/parallax_risk/common/money.py`.
- Market/curves: `src/parallax_risk/domain/market/`.
- Contracts/pricing: `src/parallax_risk/domain/instruments/`, `domain/pricing/`.
- Boundaries/workflow: `src/parallax_risk/application/`.
- Tests: `tests/`; documentation: `docs/INDEX.md`, `docs/CODEBASE_GUIDE.md`.
- Decisions: `docs/decisions/README.md`; maintenance log: `CHANGELOG.md`.
