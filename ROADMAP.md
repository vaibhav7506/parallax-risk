# Parallax Risk roadmap

**Current:** Phase 11 complete, release 0.11.0.
Phases 1–11 are complete. Documentation maintenance does not advance the phase.
Phase 12 remains NOT IMPLEMENTED and requires a new `go`.

| Phase | Scope | State |
|---|---|---|
| 1 | Foundation, architecture and quantitative primitives | COMPLETE — [evidence](docs/validation/phase-1.md) |
| 2 | Market data, curves and deterministic pricing | COMPLETE — [evidence](docs/validation/phase-2.md) |
| 3 | Stochastic market models, correlation validation and calibration | COMPLETE — [evidence](docs/validation/phase-3.md) |
| 4 | Monte Carlo research engine, random streams and diagnostics | COMPLETE — [evidence](docs/validation/phase-4.md) |
| 5 | Portfolios, counterparties, netting and collateral | COMPLETE — [evidence](docs/validation/phase-5.md) |
| 6 | Exposure and wrong-way risk | COMPLETE — [evidence](docs/validation/phase-6.md) |
| 7 | XVA and extended sensitivity engine | COMPLETE — [evidence](docs/validation/phase-7.md) |
| 8 | Regulatory-style capital and challenger models | COMPLETE — [evidence](docs/validation/phase-8.md) |
| 9 | Model validation lab | COMPLETE — [evidence](docs/validation/phase-9.md) |
| 10 | Mutation, adversarial search and failure forensics | COMPLETE — [evidence](docs/validation/phase-10.md) |
| 11 | Governance, monitoring, lineage and reporting | COMPLETE — [evidence](docs/validation/phase-11.md) |
| 12 | Financial APIs/workflows, scale, security and release hardening | PLANNED / NOT IMPLEMENTED |

Operational API/CLI and foundation metadata exist; they do not implement financial
HTTP jobs or authenticated governance approval. Phase 4 implements explicit stochastic sequence replay. Proposed decisions
are tracked separately in the [decision register](docs/decisions/README.md).
