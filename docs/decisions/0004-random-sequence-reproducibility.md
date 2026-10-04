# ADR 0004 — Random sequence reproducibility

**Status:** Accepted for run metadata; Proposed for random-sequence policy.
**Implementation:** Random generator/sequence/simulation NOT IMPLEMENTED.
**Recorded:** 2026-10-01.

## Context
A seed alone cannot identify future random draws if generator, ordering or stream
allocation changes. Current deterministic prices still need reproducible inputs.

## Decision
The implemented `RunContext` freezes run ID, aware UTC timestamp, uint64 seed and
canonical nonsecret configuration hash. Inject ID/time for identical envelope replay.
Phase 2 prices additionally identify market, curves, instrument and model version.
Seed is metadata and does not influence current deterministic valuation.
Phase 3 calibration records its ID, objective input/settings hashes, bounds, fitted
parameters, model version and enclosing RunContext; no random draws are consumed.

The proposed future sequence policy requires explicit generator/algorithm/version,
seed, stream/sequence assignment and ordering. Record runtime/library/source revision
where available and test replay when random-sequence code is authorized. No algorithm
is selected by this record and no global RNG or random-stream adapter exists now.

## Alternatives considered
Seed-only metadata is cheap but insufficient for sequence replay. Global RNGs are
convenient but couple runs and execution order. Explicit stream allocation takes
more configuration and is proposed for later implementation.

## Why this decision
Separating accepted metadata from proposed sequence behavior avoids promising
stochastic reproducibility before a generator and tests exist.

## Consequences
Current envelope/hash replay is testable. A fresh context has a fresh ID/time;
it is not byte-identical unless those fields are injected.

## Risks
Same seed across different algorithms/environments may give different sequences.
Calibration records input/settings hashes, ID and fitted parameters. Source commit,
portfolio/sequence lineage remains incomplete. Numerical library/BLAS changes can
alter fits; same-environment replay and cross-platform finite tolerances differ.

## Follow-up
Revisit generator/sequence decisions in their authorized stochastic/research phases;
do not implement them during documentation maintenance.

## Related code
`src/parallax_risk/application/context.py` (`RunContext`, `create_run_context`),
`src/parallax_risk/application/config.py` (`Settings`),
`tests/unit/test_config_context_logging.py`,
`tests/integration/test_deterministic_workflow.py`.
See [reproduction guide](../REPRODUCIBILITY.md).
`src/parallax_risk/domain/calibration/contracts.py`,
`tests/quantitative/test_calibration.py`.

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Run ID/time/seed/configuration envelope introduced; no RNG | [Phase 1](../validation/phase-1.md) |
| 2 | Deterministic market/curve/instrument/model evidence and replay added; no RNG | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Proposed sequence policy made explicit; implemented metadata unchanged | [Register](README.md) |
| 3 | Calibration input/settings/parameter/run evidence added; RNG/sequence remains NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
