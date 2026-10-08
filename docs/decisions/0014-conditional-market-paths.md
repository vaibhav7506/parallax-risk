# ADR 0014 — Conditional market paths and retained fixings

**Status:** Accepted; implemented and verified in Phase 6. **Recorded:** 2026-10-01.

## Context

Future exposure needs prices conditional on current state and fixings known at that date.

## Decision

Build immutable synthetic/derived snapshots and model bond curves per path/date. Require exact ACT/365F date alignment, explicit Q rate/FX bindings and curve knots. Generate future fixings once on the supplied grid and retain them unchanged; origin fixings are caller supplied.

## Alternatives considered

Reusing the origin curve would omit future conditioning. Reprojecting historical fixings introduces lookahead and changes contractual known payments. Unlabelled derived quotes misrepresent model values as observations.

## Consequences

Conditional prices use existing pricer/portfolio ports. No pricing formula, market authenticity claim or API handler is replaced. Explicit interpolation between model bond knots remains approximate.

## Risks

Multi-currency stochastic-rate FX drift is caller responsibility; correlation alone does not guarantee arbitrage consistency. Single-curve projection, synthetic provenance and no extrapolation limit scope.

## Related code

`src/parallax_risk/domain/exposure/markets.py`, `tests/integration/test_exposure_workflow.py`.
[Methodology](../methodology/EXPOSURE.md), [credit/WWR](../methodology/WRONG_WAY_RISK.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Introduced explicit policy and implementation; verified on both platforms | [Phase 6](../validation/phase-6.md) |
