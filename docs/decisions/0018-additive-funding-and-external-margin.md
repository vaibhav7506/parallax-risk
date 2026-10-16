# ADR 0018 — Additive funding proxy and external segregated margin

**Status:** Accepted; implemented and verified in Phase 7. **Recorded:** 2026-10-01.

## Context

FVA/MVA require stated funding needs, benchmarks and margin ownership. Existing CSA reusable independent amount is not segregated posted IM.

## Decision

Use annual nonnegative deterministic excess spread curves. FCA integrates discounted EE as a borrowing proxy; optional explicit FBA integrates ENE as a lending proxy. FVA=-FCA+FBA. MVA integrates supplied expected segregated posted IM separately, excluding it from FCA. Amounts interpolate linearly and discounted amounts use trapezoids on a knot union. All assumptions and profile sources are retained.

## Alternatives considered

A recursive hedge/treasury pricing framework would need additional cash/default/replication contracts. Inferring regulatory IM or reusing CSA IA would manufacture missing behavior. Automatic lending benefit is rejected in favor of an explicit boolean policy.

## Consequences

Funding and IM are externally supplied, validated and held fixed in listed risk bumps. All components sum in one reporting currency without cross-name netting. Zero IM or disabled lending benefit remains explicit.

## Risks

No default termination, recursive pricing, hedge financing, collateral interest or regulatory IM estimation. Additive components can economically overlap depending on supplied spreads; no replication or automatic double-counting avoidance is claimed.

## Related code

`src/parallax_risk/domain/xva/contracts.py`, `src/parallax_risk/domain/xva/calculators.py`, `tests/quantitative/test_xva.py`.
[Methodology](../methodology/FUNDING_MARGIN.md), [workflow](../workflows/XVA_WORKFLOW.md).

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
