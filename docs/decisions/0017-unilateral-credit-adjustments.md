# ADR 0017 — Unilateral credit adjustments and sampled dependent loss

**Status:** Accepted; implemented and verified in Phase 7. **Recorded:** 2026-10-01.

## Context

Exposure statistics alone are not valuation adjustments. Dependence requires actual default-weighted loss rather than an independent EE times PD shortcut.

## Decision

Use deterministic-discount independent unilateral CVA/DVA integration on the union of profile/discount/hazard knots. Default masses are exact; discounted profiles use endpoint averages. For dependent counterparty scenarios use mean discounted right-grid EAD times LGD without a second PD multiplier. Own DVA remains explicitly independent unilateral. Signed CVA is negative and DVA positive; finite ACT/365F horizons and currencies must align.

## Alternatives considered

First-to-default bilateral closeout would require joint default/settlement semantics not provided by Phase 6. Multiplying dependent EE by marginal PD loses dependence. Sampled default loss is required for the chosen scenarios; an unlabelled fallback is rejected.

## Consequences

Retain credit method and input fingerprints, per-interval labels, generic signed component/result reconciliation and per-counterparty aggregation. XvaService injects the calculator and verifies exact source evidence. No financial API or persistence is introduced.

## Risks

Right-grid alive collateral omits default-conditioned freeze/MPOR and may bias loss near maturity. Deterministic discounting omits covariance. Unilateral components do not establish a bilateral replication price. Static rank is non-adapted; dynamic marginals may change.

## Related code

`src/parallax_risk/domain/xva/calculators.py`, `src/parallax_risk/domain/xva/contracts.py`, `src/parallax_risk/application/xva.py`, `tests/quantitative/test_xva.py`.
[Methodology](../methodology/XVA.md), [workflow](../workflows/XVA_WORKFLOW.md).

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
