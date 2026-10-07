# ADR 0011 — Batched vectorized paths and Gaussian innovation covariance

**Status:** Accepted; implemented in Phase 4. **Recorded:** 2026-10-01.

## Context

Full path allocation scales with total paths, states and times. Exact OU endpoint
innovations do not have the same correlation as their underlying Brownian drivers.
Mutable NumPy output also needs a clear ownership contract.

## Decision

Stream path batches with path/step/factor draw order; publish defensive immutable
little-endian C-order byte buffers. Keep NumPy working arrays private to execution.
Validate vectorized transitions against the scalar strategies. Interpret supplied
correlations as pre-loading Brownian-driver correlations and normalize exact OU
kernel covariances per time step before Cholesky. Heston's pre-loading pair stays
independent so intrinsic rho is applied once. Use fixed factor reduction order.
Require numerical positive definiteness; there is no singular-factor fallback.

## Alternatives considered

Materializing all paths simplifies consumers but loses bounded batch storage.
Read-only flags on mutable-owned arrays can be reversed. Applying the same rho to
OU and unweighted endpoint shocks misstates finite-step covariance. Generic scalar
loops retain simple reuse but fail the requested vectorized research workload.

## Consequences

Each iterator owns its state and RNG. Batch-size replay is tested on pinned builds.
Exact Gaussian/log-GBM endpoint dependence is consistent with Brownian correlations;
Euler/Heston remain numerical schemes. Immutable publication requires a copy.

## Risks

Collectors can retain every buffer and defeat streaming. Tracemalloc excludes some
native allocations and is not RSS. Exact rates still omit joint integrated discounts.
Library/build/CPU changes can change draws or floating-point outputs. Sobol high
dimension/order can weaken gains; no Brownian bridge or PCA is implemented.

## Related code

`src/parallax_risk/domain/simulation/arrays.py`,
`src/parallax_risk/domain/simulation/kernels.py`,
`src/parallax_risk/domain/simulation/engine.py`,
`src/parallax_risk/application/simulation_benchmark.py`,
`tests/quantitative/test_simulation_paths.py`.
[Paths](../methodology/MONTE_CARLO.md), [benchmarks](../validation/MONTE_CARLO_BENCHMARKS.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; path engine NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; path engine NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Scalar model/correlation primitives supply the foundation; paths NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Vectorized batched paths, immutable buffers, exact Gaussian innovation covariance and measured benchmark harness introduced | [Phase 4](../validation/phase-4.md) |
| 5 | Reviewed; no change; Phase 5 deterministic portfolios retain this accepted contract | [Phase 5](../validation/phase-5.md) |
