# ADR-0003: PostgreSQL behind a lifecycle-owned connectivity port

**Status:** Accepted
**Date:** 2026-09-30
**Deciders:** Parallax Risk implementation (institutional review pending)

## Context
Phase 1 needs a real PostgreSQL boundary without prematurely designing governance
tables. Domain and application contracts must not expose sessions or ORM entities.

## Decision
Define ConnectivityProbe in the application layer; implement it with a lazy
SQLAlchemy 2 engine and psycopg in infrastructure. API lifespan and CLI own cleanup.
Readiness executes SELECT 1 with finite pool/connect/statement timeouts. Errors
are sanitized. No schema or migrations are created before Phase 11.

## Options considered
| Option | Complexity | Cost | Scalability | Familiarity |
|---|---|---|---|---|
| SQLAlchemy adapter behind protocol | Moderate | Low | Controlled connection pool | Standard Python persistence |
| ORM session in domain models | Low initial | High coupling | ORM-bound execution | Common but unsuitable here |
| Mock readiness until governance phase | Low | Misleading availability | No real dependency validation | Simple test pattern |

## Trade-off analysis
Synchronous DB access runs off the API event loop. An async adapter could be added
later without changing the port if justified. Mocks exercise failures and ownership;
a marked real-PostgreSQL test and CI service exercise actual connectivity.

## Consequences
Missing/unreachable DB returns 503; liveness stays independent. No SQLite fallback
exists. Alembic is declared but migrations/tables remain unimplemented in Phase 1.
Single-host URLs without query parameters are the explicit foundation limitation.

## Action items
1. [x] Implement lazy adapter, ownership and failure tests.
2. [x] Configure real PostgreSQL CI and Compose services.
