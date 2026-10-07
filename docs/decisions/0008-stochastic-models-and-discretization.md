# ADR 0008 — Stochastic model and discretization primitives

**Status:** Accepted; implemented in Phase 3. **Recorded:** 2026-10-01.

## Context

Model mathematics must be validated before a Monte Carlo engine is built. Rates
need exact Gaussian benchmarks; Heston needs explicit positivity and integration
policies. A piecewise market curve has no universally smooth derivative for Hull–White.

## Decision

Use immutable finite state tuples and common drift/diffusion/discretization protocols.
Steps consume independent standardized shocks from callers. Implement Q Vasicek and
Hull–White plus explicitly supplied-drift GBM and Q Heston. Provide exact marginal
Vasicek/Hull–White/GBM transitions and generic Euler; reject unsupported exact requests.
Hull–White uses explicit LinearForwardCurve, never guessed piecewise derivatives.
Heston projected variance/log-spot Euler reports projection and makes no boundary
convergence claim. Its European calls use stable Riccati/Lewis infinite quadrature
with numerical diagnostics and rejection gates. Phase 3 introduced no random/path engine;
Phase 4 adds the separate engine and reconciled vectorized kernels.

## Alternatives considered

Embedded RNG/model paths would pre-build Phase 4 and entangle mathematical tests.
Silent Heston variance clipping would conceal discretization bias. Full-truncation,
QE and exact Heston schemes are valuable alternatives requiring separate validation.
Automatic interpolation derivatives would fabricate Hull–White curve smoothness.

## Why this decision

Supplied shocks isolate coefficients and transition error. Explicit smoothing/schemes
and quadrature diagnostics make approximations reviewable and failures reproducible.

## Consequences

Model primitives can be used independently of HTTP, ORM and random generation.
Analytical bonds/options support meaningful calibration examples. Existing Phase 2
deterministic pricing keeps model version 0.2.0 while new models are version 0.3.0.

## Risks

Gaussian rates allow negative values. One-factor/constant-parameter models omit
real-market complexity. Heston projection is biased; Fourier estimates are not rigorous
error bounds. Supplied correlated shocks would double-apply Heston correlation.

## Follow-up

Phase 4 implements separate streams and joint paths; exact stochastic discount-integral
transitions are still absent from exact marginal rate steps.

## Related code

`src/parallax_risk/domain/models/base.py`, `rates.py`, `assets.py`,
`discretization.py` and `heston_pricing.py` in that directory.
`tests/quantitative/test_stochastic_models.py`, `tests/unit/test_model_guards.py`.
[Methodology](../methodology/STOCHASTIC_PROCESSES.md), [Heston](../methodology/HESTON.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; models NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; deterministic domain only | [Phase 2](../validation/phase-2.md) |
| 3 | Model interfaces, exact/Euler primitives and analytical/Fourier instrument pricing introduced | [Phase 3](../validation/phase-3.md) |
| 4 | Scalar model policies retained; vectorized kernels reconciled and projected-Heston counts reported by the separate engine | [Phase 4](../validation/phase-4.md) |
| 5 | Reviewed; no change; Phase 5 deterministic portfolios retain this accepted contract | [Phase 5](../validation/phase-5.md) |
