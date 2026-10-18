# ADR 0006 — Persistence boundaries

**Status:** Superseded in Phase 11 by [ADR 0029](0029-governance-persistence.md); original connectivity contract retained. **Recorded:** 2026-10-01; reconstructs Phase 1 choice.

## Context
This record preserves the prior no-schema decision. Current persistence is documented in [ADR 0029](0029-governance-persistence.md).

Readiness must check a real database without pulling ORM types into quantitative code.

## Decision
Use the application `ConnectivityProbe` protocol and an explicitly constructed
SQLAlchemy PostgreSQL adapter. The adapter performs SELECT 1 only, with bounded
timeouts and sanitized failures. API lifespan/CLI owns cleanup. No tables or automatic
migrations exist. Credentials are excluded from public configuration and hashes.

## Alternatives considered
ORM in domain code couples pricing to persistence. A fake healthy status conceals
missing infrastructure. SQLite production fallback changes the required backend.

## Why this decision
Actual dependency failure is visible while financial code remains independently usable.

## Consequences
Readiness can be 503 even when liveness is 200. PostgreSQL integration is separately
tested. Governance persistence is DEFERRED to its authorized phase.

## Risks
Connectivity alone does not prove schema readiness, data integrity, authorization
or availability guarantees. Single-host connection settings are deliberately limited.

## Follow-up
Introduce migrations only when actual persisted entities are authorized, with new
tests and an updated readiness/schema policy.

## Related code
`src/parallax_risk/application/ports.py` (`ConnectivityProbe`),
`src/parallax_risk/infrastructure/persistence/database.py` (`PostgresConnectivity`),
`tests/integration/test_database_cli.py`.

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Port, bounded PostgreSQL adapter and operational readiness introduced | [Phase 1](../validation/phase-1.md) |
| 2 | Reviewed; no persistence behavior change or tables introduced | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Canonical record and scoped cleanup guidance added; DB behavior unchanged | [Register](README.md) |
| 3 | Reviewed; no tables or calibration persistence introduced | [Phase 3](../validation/phase-3.md) |
| 4 | Reviewed; no tables or research-result persistence introduced; disposable PostgreSQL verification remains scoped | [Phase 4](../validation/phase-4.md) |
| 5 | Reviewed; no change; Phase 5 deterministic portfolios retain this accepted contract | [Phase 5](../validation/phase-5.md) |
| 6 | Reviewed; no change; reused existing contract in Phase 6 | [Phase 6](../validation/phase-6.md) |
| 7 | Reviewed; no change to accepted policy; Phase 7 consumers preserve its stated limitations | [Phase 7](../validation/phase-7.md) |
| 8 | Reviewed; no change; existing contracts retained for restricted Phase 8 research | [Phase 8](../validation/phase-8.md) |
| 9 | Reviewed; no change; existing policy retained in Phase 9 lab scope | [Phase 9](../validation/phase-9.md) |
| 10 | Reviewed; no change; existing policy retained with isolated Phase 10 research workflows | [Phase 10](../validation/phase-10.md) |
| 11 | Superseded no-schema scope by ADR 0029; original connectivity contract retained | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed superseded decision; connectivity retained; successor 0029 extended by 0034 | [Phase 12](../validation/phase-12.md) |
