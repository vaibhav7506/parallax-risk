# Parallax Risk foundation architecture

Phase 1 uses a modular Python package with inward dependencies. No domain pricing
models or empty future-phase directories exist. The package has no import-time
IO, environment reads, network connections, resource creation or global logger
configuration. Python module metadata and immutable type definitions are allowed.

```mermaid
flowchart TD
    HTTP[FastAPI factory and lifespan] --> APP[Application config, context, ports]
    CLI[Operational CLI] --> APP
    HTTP --> DB[PostgreSQL adapter]
    CLI --> DB
    DB --> PORT[ConnectivityProbe port]
    APP --> CORE[Common immutable financial primitives]
    DB --> ERR[Core errors]
    HTTP --> LOG[Instance-local structured logging]
    CLI --> LOG
```

`common` owns nominal IDs, exact decimal Money, finite scalar operations, civil
date/time and calendar conventions, tolerance and error contracts. It does not
import Pydantic, SQLAlchemy or FastAPI. Logging is an isolated cross-cutting module
using structlog; no quantitative primitive depends on it.

`application` owns Pydantic configuration at a boundary, canonical configuration
hashing, immutable RunContext and the connectivity protocol. It does not import
ORM or HTTP types. No risk workflows are scaffolded yet.

`infrastructure.persistence` adapts SQLAlchemy to the connectivity protocol. An
engine is constructed explicitly at CLI invocation or API lifespan startup, with
lazy connections, finite pool limits, and connect/statement timeouts. SELECT 1
is its only query. Exceptions are sanitized at this adapter; no tables exist.

`api` and `cli` are composition roots and own the lifetime of injected probes.
Readiness probes run in a thread pool so synchronous PostgreSQL calls cannot
block the event loop. Liveness does not depend on external availability. Missing
database configuration is visible as 503, never a false healthy persistence claim.

Imports and layer contracts have automated tests. Logs contain restricted event,
outcome, error-type and optional run-ID fields, without raw portfolio/market data
or connection strings. Later phases must review sensitivity before adding fields.

The service is intentionally unauthenticated with only operational endpoints;
financial API workflows and security hardening belong to Phase 12. Expose this
baseline only on loopback/development networks. PostgreSQL is not published by
Compose. The non-root container has no source mounting or automatic migrations.

The four ADRs record accepted implementation choices, not external institutional
approval. Architecture, numerical correctness and regulatory compliance must not
be inferred solely from the project title.
