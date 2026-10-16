# ADR 0029 — Transactional governance persistence

**Status:** Accepted; implemented and verified in Phase 11. **Recorded:** 2026-10-02.

## Context
Phase 11 authorizes persisted research governance and evidence reporting while preserving independent financial mathematics and prior history.

## Decision
Supersede the no-schema scope of ADR 0006 with an explicit packaged Alembic revision 0011 and SQLAlchemy PostgreSQL head/event repository. Preserve the original ConnectivityProbe and its SELECT 1 semantics. Immutable domain records cross an injected application port; ordinary writes use expected revisions, ordered reference/target locks and atomic snapshot/audit commits. Database triggers prohibit event updates/deletes and immutable-kind head advancement. Migrations never run at import or normal startup.

## Alternatives considered
Mutable overwritten metadata loses history. ORM dependencies in the domain breach the accepted architecture. Silent fallback or invented narrative conceals failures. Automatic imports/startup migrations obscure resource lifetimes and deployment selection.

## Consequences
The implemented workflow requires explicit inputs, injected resources and reproducible retained evidence. See [contracts](../methodology/GOVERNANCE.md) and [workflow](../workflows/GOVERNANCE_WORKFLOW.md).

## Risks
Declared actors are unauthenticated. Raw administrators can disable triggers; hashes are not signatures. The whole synthetic demo is not one transaction. Upgrade selection and privileges remain caller-owned; destructive base downgrade requires opt-in. Readiness does not prove schema readiness.

## Related code
`src/parallax_risk/infrastructure/persistence/governance.py`, `tests/unit/test_governance.py`, `tests/integration/test_governance_postgres.py`.

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
