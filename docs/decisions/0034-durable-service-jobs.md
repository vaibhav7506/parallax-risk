# ADR 0034 — Durable owned jobs and success-linked lineage

**Status:** Accepted; implemented in Phase 12; final release verification complete. **Recorded:** 2026-10-02.

## Context
The final service must expose real research engines with explicit reproducibility, financial contracts and bounded resources. Existing Phases 1–11 contracts remain evidence.

## Decision
PostgreSQL 0012 retains immutable owned inputs/requests/results. Global transactional admission, owner idempotency, SKIP LOCKED claims and CAS completion guard the state machine. Success requires committed lineage. Uncertain persistence halts a local worker and never auto-retries.

## Alternatives considered
An in-memory queue loses replay after restart. Redis/distributed workers were not justified by measured small-job performance. Existing governor tables remain unchanged.

## Consequences
See [service contracts](../methodology/SERVICE.md), [operations](../operations/SERVICE.md) and [benchmarks](../validation/SERVICE_BENCHMARKS.md). No unrelated future implementation is added.

## Risks
Lineage/completion transactions are separate. Crash/abandonment may leave committed lineage and an uncertain run requiring inspection; no hard cancellation or HA is claimed.

## Related code
`src/parallax_risk/infrastructure/persistence/service.py`, `tests/integration/test_service_postgres.py`, `tests/unit/test_service_wire.py`.

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
| 11 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 11](../validation/phase-11.md) |
| 12 | Introduced; actual service/financial checks and final verification passed on both platforms | [Phase 12](../validation/phase-12.md) |
