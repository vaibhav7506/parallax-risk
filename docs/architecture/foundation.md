# Parallax Risk foundation architecture

Phases 1–4 use a modular Python package with inward dependencies. Deterministic
domain pricing is implemented; future-phase directories are not scaffolded.
The package has no import-time
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
    APP --> DOMAIN[Market snapshots, curves, contracts and pricing]
    DOMAIN --> CORE
    DB --> ERR[Core errors]
    HTTP --> LOG[Instance-local structured logging]
    CLI --> LOG
```

`common` owns nominal IDs, exact decimal Money, finite scalar operations, civil
date/time and calendar conventions, tolerance and error contracts. It does not
import Pydantic, SQLAlchemy or FastAPI. Logging is an isolated cross-cutting module
using structlog; no quantitative primitive depends on it.

`application` owns Pydantic configuration at a boundary, canonical configuration
hashing, immutable RunContext and the connectivity protocol. Phase 2 adds frozen
Pydantic market ingestion and an injected pricing workflow returning run-correlated
domain results. It does not import ORM or HTTP types.

`domain` owns immutable market observations/snapshots, curve representations,
bounded deterministic bootstrap, contracts, valuation evidence and sensitivities.
The Phase 2 financial arithmetic uses common primitives and the standard library;
model/simulation mathematics additionally uses NumPy/SciPy. Domain never imports
Pydantic, HTTP, ORM or application types. Curve construction and pricing
are explicit calls with no process-global caches. Source-labelled observations
remain separate from derived curves; the result hashes both. The bootstrap quote
protocol describes extension points, while Phase 2 supports deposits and par swaps.
Floating cash-flow abstraction supports the implemented simple-index contract;
compounded floating-index and pathwise stochastic repricing logic is absent.

Phase 3 adds separate model/objective packages and an injected calibration service/
SciPy optimizer adapter. Single-step models consume supplied shocks; they do not
create random paths. See [current components](COMPONENTS.md) and
[model decision](../decisions/0008-stochastic-models-and-discretization.md).

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

The ADRs record accepted implementation choices, not external institutional
approval. Architecture, numerical correctness and regulatory compliance must not
be inferred solely from the project title.

The [canonical decision register](../decisions/README.md) now tracks per-phase
changes and reviews. Original ADRs remain historical evidence; see the
[current architecture overview](OVERVIEW.md) for navigation.
