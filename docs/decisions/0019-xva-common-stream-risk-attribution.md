# ADR 0019 — Common-stream XVA revaluation and explicit movement residual

**Status:** Accepted; implemented and verified in Phase 7. **Recorded:** 2026-10-01.

## Context

Risk estimates need admissible parameter transformations and distinguish sampling/kink error from true factor movement. Attribution must not hide omitted changes.

## Decision

Revalue actual production exposure/XVA at 0, +/-h and +/-h/2 under identical addressed market/default/rank streams. Support bound rate/FX/volatility, credit triangle spread, recovery, Brownian correlation and CSA receive threshold. Retain all results, per-unit derivatives and actual stability. Attribute ordered exact revaluation steps and independently valued actual endpoint; always report component and total residuals.

## Alternatives considered

Cached linear Greeks do not implement actual bump/reprice. Independent seeds add avoidable sampling noise. One-sided fallback, parameter clamping and correlation repair hide inadmissibility. Shapley allocation is deferred; sequential allocation is explicitly order dependent.

## Consequences

Typed exact factor targets and named unique movements reject malformed/unsupported transformations. Correlation tolerance is preserved. Custom dynamic credit policies and shared single-name spread states cannot be silently replaced. Origins/funding/IM and stream addresses remain fixed.

## Risks

Sampled defaults are bucketed and can yield flat/unstable finite differences. Common streams do not guarantee accuracy. Credit spread is not calibrated quote CS01; discrete CSA terms and Heston vega are unsupported. Attribution is not causal or Shapley.

## Related code

`src/parallax_risk/domain/xva/risk.py`, `src/parallax_risk/application/xva_revaluation.py`, `tests/integration/test_xva_workflow.py`.
[Methodology](../methodology/XVA_SENSITIVITIES.md), [workflow](../workflows/XVA_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; Phase 7 XVA/risk policy NOT IMPLEMENTED | [Phase 6](../validation/phase-6.md) |
| 7 | Introduced explicit policy and implementation; verified on both platforms; actual evidence retained separately | [Phase 7](../validation/phase-7.md) |
| 8 | Reviewed; no change; existing contracts retained for restricted Phase 8 research | [Phase 8](../validation/phase-8.md) |
| 9 | Reviewed; no change; existing policy retained in Phase 9 lab scope | [Phase 9](../validation/phase-9.md) |
| 10 | Reviewed; no change; existing policy retained with isolated Phase 10 research workflows | [Phase 10](../validation/phase-10.md) |
| 11 | Reviewed; no change; existing numerical contracts retained by evidence/report consumers | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed; no change; numerical/research contract remains applicable | [Phase 12](../validation/phase-12.md) |
