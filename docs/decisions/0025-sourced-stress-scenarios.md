# 0025 — Sourced and ordered stress scenarios

**Status:** Accepted; Phase 9 implemented and verified.

## Context

Inventing history or inferring event probability from supplied shocks would misrepresent evidence.

## Decision

Revalue typed hypothetical shocks and dated caller-sourced before/after observations with exact factor units. Ordered combined shocks retain parent hashes and actual outputs/movements. Enforce unique names, admissible intermediate states and evaluation budgets.

## Alternatives

Implicit conversion, silent numerical repair and fabricated adapters were rejected.
Existing NumPy/SciPy and injected library workflows avoid required external engines.

## Consequences

Evidence is explicit and reproducible, with failures retained. No persistence or financial HTTP job is introduced.

## Risks

Caller source labels are not authenticated historical data. Interactions are order dependent; funding/IM/fixings follow existing fixed-bump assumptions.

## Related code

`src/parallax_risk/application/validation_stress.py`, `src/parallax_risk/application/xva_revaluation.py`.

[Methodology](../methodology/MODEL_VALIDATION.md), [workflow](../workflows/VALIDATION_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 6](../validation/phase-6.md) |
| 7 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 7](../validation/phase-7.md) |
| 8 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 8](../validation/phase-8.md) |
| 9 | Introduced; implementation and explicit scope recorded | [Phase 9](../validation/phase-9.md) |
| 10 | Reviewed; no change; existing policy retained with isolated Phase 10 research workflows | [Phase 10](../validation/phase-10.md) |
