# ADR 0004 — Random sequence reproducibility

**Status:** Accepted; run metadata and sequence policy implemented through Phase 4.
**Recorded:** 2026-10-01. Earlier proposed policy remains in the phase history.

## Context

A seed alone cannot identify draws when generator, transform, draw order, stream
allocation, model, grid or environment changes. Deterministic workflows also need
input and run evidence.

## Decision

Keep RunContext identity, aware UTC time, uint64 root seed and nonsecret config hash.
Model prices and calibration retain their own input/settings/model evidence.
Phase 4 uses order-independent StreamKey(seed, stream, substream), explicit
SeedSequence addresses and PCG64DXSM Ziggurat pseudo normals. Sobol uses explicit
LMS+shift scrambling, complete powers of two and the recorded finite-bit midpoint
inverse-normal convention. Pair reflection is adjacent and preserves whole pairs.
Record request hash, algorithm/transform/layout, engine/model configuration,
Python/NumPy/SciPy/platform and optional supplied source revision. No global RNG,
wall-clock seed or hidden fallback. Each execution owns its mutable stream.

## Alternatives considered

Seed-only metadata misses method/order/environment changes. A global RNG couples
runs and allocation order. OS-entropy defaults defeat explicit replay. Batch-specific
seeds change paths when batch size changes. Counter-based engines remain possible
future policies, not implicit substitutions for the selected algorithm.

## Why this decision

Explicit addressed streams and fixed ordering permit reproducible, isolated research
and independent pilot/scramble allocation. Pinned-environment batching is tested.

## Consequences

Fresh ID/time changes the run envelope but not draws. Complete metadata distinguishes
content replay from statistical correctness. Source revision can be None in an
uncommitted workspace; no commit is fabricated.

## Risks

Stream separation is probabilistic. NumPy does not guarantee normal-transform
compatibility across every future version, call shape, build or CPU. Sobol's finite-bit
normal convention introduces quadrature bias. Same-environment exact replay and
cross-platform finite-tolerance validation are different guarantees.

## Related code

`src/parallax_risk/application/context.py`,
`src/parallax_risk/domain/simulation/random.py`,
`src/parallax_risk/domain/simulation/contracts.py`,
`src/parallax_risk/domain/simulation/engine.py`,
`tests/unit/test_simulation_random.py`, `tests/quantitative/test_simulation_paths.py`.
[Reproduction](../REPRODUCIBILITY.md), [paths](../methodology/MONTE_CARLO.md),
[ADR 0010](0010-independent-sampling-units.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Run ID/time/seed/configuration envelope introduced; no RNG | [Phase 1](../validation/phase-1.md) |
| 2 | Deterministic market/curve/instrument/model evidence and replay added; no RNG | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Proposed sequence policy made explicit; implemented metadata unchanged | [Register](README.md) |
| 3 | Calibration input/settings/parameter/run evidence added; RNG/sequence remains NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Prior sequence proposal accepted: addressed PCG64DXSM/Sobol streams, ordering, transforms, environment metadata and replay tests | [Phase 4](../validation/phase-4.md) |
| 5 | Reviewed; no change; Phase 5 deterministic portfolios retain this accepted contract | [Phase 5](../validation/phase-5.md) |
