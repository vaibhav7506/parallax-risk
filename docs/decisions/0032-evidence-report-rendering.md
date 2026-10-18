# ADR 0032 — Evidence-only HTML and JSON reports

**Status:** Accepted; implemented and verified in Phase 11. **Recorded:** 2026-10-02.

## Context
Validation, stress, convergence and mutation engines already produce typed evidence,
including failures and missed mutations. Phase 11 needs both inspectable reports
and machine-readable records without replacing those results with inferred claims.

## Decision
Build seven report kinds from typed computed validation/governance/comparison/stress/convergence/mutation/lineage results. Preserve assumptions, failures, residuals and misses with a synthetic flag, evidence digest, UTC generation time and explicitly caller-authored interpretation. Render deterministic schema-1 JSON and HTML with escaped stored strings and restrictive CSP. No LLM-generated conclusions or PDF dependency.

## Alternatives considered
Generated narrative could assert conclusions absent from the numerical evidence.
HTML alone is inconvenient for programmatic replay; JSON alone makes human review
harder. PDF adds another renderer and dependency without a current requirement.
HTML/JSON pairs retain the actual result and separate caller interpretation from
computed evidence. Escaping and restrictive CSP constrain stored-content rendering.

## Consequences
The implemented workflow requires explicit inputs, injected resources and reproducible retained evidence. See [contracts](../methodology/GOVERNANCE.md) and [workflow](../workflows/GOVERNANCE_WORKFLOW.md).

## Risks
Trusted result providers/callers own evidence provenance and narrative. Dataclass type metadata and nested canonical evidence text are part of the JSON contract. Digests are not signatures. Byte determinism is conditional on identical metadata and numerical results, not cross-platform equivalence.

## Related code
`src/parallax_risk/application/governance_reports.py`, `tests/unit/test_governance.py`, `tests/integration/test_governance_postgres.py`.

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
| 9 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 9](../validation/phase-9.md) |
| 10 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 10](../validation/phase-10.md) |
| 11 | Introduced; reviewed and verified on Windows/installed-wheel Linux with live PostgreSQL | [Phase 11](../validation/phase-11.md) |
| 12 | API report creation reads compatible retained owned jobs; summary synthetic status explicitly declared | [Phase 12](../validation/phase-12.md) |

## Phase 12 applicability

API report creation reads compatible retained owned jobs; summary synthetic status explicitly declared. See [service contracts](../methodology/SERVICE.md). Earlier history remains evidence; this extends the decision without replacing its accepted financial policy.
