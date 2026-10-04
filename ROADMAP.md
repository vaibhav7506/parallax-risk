# Parallax Risk roadmap

**Current:** Phase 3 complete, release 0.3.0. Phases 1–3 are complete.
Documentation maintenance does not advance the phase. Phase 4 remains NOT IMPLEMENTED
and requires a new `go`.

| Phase | Scope | State |
|---|---|---|
| 1 | Foundation, architecture and quantitative primitives | COMPLETE — [evidence](docs/validation/phase-1.md) |
| 2 | Market data, curves and deterministic pricing | COMPLETE — [evidence](docs/validation/phase-2.md) |
| 3 | Stochastic market models, correlation validation and calibration | COMPLETE — [evidence](docs/validation/phase-3.md) |
| 4 | Monte Carlo research engine, random streams and diagnostics | PLANNED / NOT IMPLEMENTED |
| 5 | Portfolios, counterparties, netting and collateral | PLANNED / NOT IMPLEMENTED |
| 6 | Exposure and wrong-way risk | PLANNED / NOT IMPLEMENTED |
| 7 | XVA and extended sensitivity engine | PLANNED / NOT IMPLEMENTED |
| 8 | Regulatory-style capital and challenger models | PLANNED / NOT IMPLEMENTED |
| 9 | Model validation lab | PLANNED / NOT IMPLEMENTED |
| 10 | Mutation, adversarial search and failure forensics | PLANNED / NOT IMPLEMENTED |
| 11 | Governance, monitoring, lineage and reporting | PLANNED / NOT IMPLEMENTED |
| 12 | Financial APIs/workflows, scale, security and release hardening | PLANNED / NOT IMPLEMENTED |

Operational API/CLI and foundation metadata exist; they do not implement financial
risk jobs, governance approval or stochastic sequence replay. Proposed decisions
are tracked separately in the [decision register](docs/decisions/README.md).
