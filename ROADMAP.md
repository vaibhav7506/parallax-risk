# Parallax Risk roadmap

**Current:** Phase 6 complete, release 0.6.0.
Phases 1–6 are complete. Documentation maintenance does not advance the phase.
Phase 7 remains NOT IMPLEMENTED and requires another `go`.

| Phase | Scope | State |
|---|---|---|
| 1 | Foundation, architecture and quantitative primitives | COMPLETE — [evidence](docs/validation/phase-1.md) |
| 2 | Market data, curves and deterministic pricing | COMPLETE — [evidence](docs/validation/phase-2.md) |
| 3 | Stochastic market models, correlation validation and calibration | COMPLETE — [evidence](docs/validation/phase-3.md) |
| 4 | Monte Carlo research engine, random streams and diagnostics | COMPLETE — [evidence](docs/validation/phase-4.md) |
| 5 | Portfolios, counterparties, netting and collateral | COMPLETE — [evidence](docs/validation/phase-5.md) |
| 6 | Exposure and wrong-way risk | COMPLETE — [evidence](docs/validation/phase-6.md) |
| 7 | XVA and extended sensitivity engine | PLANNED / NOT IMPLEMENTED |
| 8 | Regulatory-style capital and challenger models | PLANNED / NOT IMPLEMENTED |
| 9 | Model validation lab | PLANNED / NOT IMPLEMENTED |
| 10 | Mutation, adversarial search and failure forensics | PLANNED / NOT IMPLEMENTED |
| 11 | Governance, monitoring, lineage and reporting | PLANNED / NOT IMPLEMENTED |
| 12 | Financial APIs/workflows, scale, security and release hardening | PLANNED / NOT IMPLEMENTED |

Operational API/CLI and foundation metadata exist; they do not implement financial
risk jobs or governance approval. Phase 4 implements explicit stochastic sequence replay. Proposed decisions
are tracked separately in the [decision register](docs/decisions/README.md).
