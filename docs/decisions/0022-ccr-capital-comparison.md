# 0022 — CCR comparison, capital inputs and exceptions

**Status:** Accepted. Introduced Phase 8, 2026-10-01.

## Context

Comparison needs interpretable differences without pretending a reduced prototype
implements a jurisdictional capital framework or model-governance approval.

## Decision

Use matching legal scope/currency, explicit challenger alpha and policy hash.
Report challenger-minus-standardized EAD and illustrative caller-weighted RWA and
capital differences. Explain the arithmetic component bridge with an explicit
rounding residual and margin-cap component. Require both strict absolute and
relative exception thresholds; at zero reference, report null relative ratio and
use absolute tolerance alone. Flags are comparison exceptions, not Findings.

## Alternatives

Inferred weights or regulatory certification overstate available functionality.
Zero denominator replacement creates artificial percentages. Causal or sensitivity
attribution would require counterfactual revaluation rather than this identity.

## Consequences

Results retain actual input/path/configuration evidence and explicit sample labels.
No persistence schema, approval workflow or HTTP financial job is introduced.
Standardized PFE remains distinct from empirical quantile PFE.

## Risks

Policy thresholds are user assumptions. Small reference EAD amplifies ratios;
an arithmetic bridge is not economic causal explanation. No regulatory capital
rulebook, stress maximum or CVA charge is supplied.

## Related code

`src/parallax_risk/domain/ccr/comparison.py`, `src/parallax_risk/application/ccr_examples.py`,
`scripts/demo_ccr.py`, `tests/quantitative/test_ccr.py`.
[Methodology](../methodology/CCR_COMPARISON.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 6](../validation/phase-6.md) |
| 7 | Not applicable; Phase 8 comparison NOT IMPLEMENTED | [Phase 7](../validation/phase-7.md) |
| 8 | Introduced explicit capital assumptions, arithmetic bridge and threshold semantics; verified on both platforms | [Phase 8](../validation/phase-8.md) |
| 9 | Reviewed; no change; existing policy retained in Phase 9 lab scope | [Phase 9](../validation/phase-9.md) |
| 10 | Reviewed; no change; existing policy retained with isolated Phase 10 research workflows | [Phase 10](../validation/phase-10.md) |
| 11 | Reviewed; no change; existing numerical contracts retained by evidence/report consumers | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed; no change; numerical/research contract remains applicable | [Phase 12](../validation/phase-12.md) |
