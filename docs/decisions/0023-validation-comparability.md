# 0023 — Comparable model outputs and reproducible findings

**Status:** Accepted; Phase 9 implemented and verified.

## Context

A loose scalar comparison hides units, stale inputs and missing drivers. Institutional governance is a later phase.

## Decision

Require identical immutable case hashes and ordered metric/unit/component schemas. Preserve challenger-minus-production components and unexplained residual. Failed tolerance checks create immutable open findings with evidence/reproduction/version; status is not approval.

## Alternatives

Implicit conversion, silent numerical repair and fabricated adapters were rejected.
Existing NumPy/SciPy and injected library workflows avoid required external engines.

## Consequences

Evidence is explicit and reproducible, with failures retained. No persistence or financial HTTP job is introduced.

## Risks

String unit labels require correct adapters; passing tolerances does not prove model adequacy. Findings are in-memory evidence, not persisted approval.

## Related code

`src/parallax_risk/domain/validation/contracts.py`, `src/parallax_risk/application/validation.py`.

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
| 11 | Reviewed; no change; existing numerical contracts retained by evidence/report consumers | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed; no change; numerical/research contract remains applicable | [Phase 12](../validation/phase-12.md) |
