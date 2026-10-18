# 0021 — Legal-unit IMM challenger

**Status:** Accepted. Introduced Phase 8, 2026-10-01.

## Context

Existing exposure profiles aggregate at counterparty level. Effective EPE needs
the legal calculation unit; counterparty profiles cannot silently replace it.

## Decision

Inject actual ExposureService and replay each enforceable set or individual
non-enforceable trade serially using the same addressed streams. Validate scoped
book/run/market/account evidence. Require an exact first-year/final-maturity node;
derive running-max effective EE and normalized right-endpoint averages. Keep
existing trapezoidal Phase 6 EPE semantics unchanged and label the new research
methodology separately. Retain configuration and path fingerprints.

## Alternatives

Fabricated internal profiles do not test the actual simulation. Counterparty-wide
netting or maximizing an already aggregated curve breaches legal scope. Grid
extrapolation and an implicit stressed calibration conceal missing assumptions.

## Consequences

Pure domain averages remain independent of application/resource lifetimes. The
application reuses existing Q repricing and margin restrictions. Per-unit output
budgets bound arrays; serial runtime scales with legal units.

## Risks

Coarse right endpoints and finite path counts can bias results. No approved/current
and stressed IMM, rollover, effective regulatory maturity or default-frozen MPOR
closeout is supplied. Common streams support replay, not model accuracy.

## Related code

`src/parallax_risk/domain/ccr/challenger.py`, `src/parallax_risk/application/ccr.py`,
`tests/integration/test_ccr_workflow.py`.
[Methodology](../methodology/IMM_CHALLENGER.md), [workflow](../workflows/CCR_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 6](../validation/phase-6.md) |
| 7 | Not applicable; Phase 8 challenger NOT IMPLEMENTED | [Phase 7](../validation/phase-7.md) |
| 8 | Introduced actual legal-unit simulation and distinct effective EE/EPE convention; verified on both platforms | [Phase 8](../validation/phase-8.md) |
| 9 | Reviewed; no change; existing policy retained in Phase 9 lab scope | [Phase 9](../validation/phase-9.md) |
| 10 | Reviewed; no change; existing policy retained with isolated Phase 10 research workflows | [Phase 10](../validation/phase-10.md) |
| 11 | Reviewed; no change; existing numerical contracts retained by evidence/report consumers | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed; no change; numerical/research contract remains applicable | [Phase 12](../validation/phase-12.md) |
