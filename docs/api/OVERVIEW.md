# API overview

Parallax Risk 0.12.0 exposes public operational endpoints and authenticated versioned
financial, validation and governance workflows. [Endpoint reference](ENDPOINTS.md),
[request/result contracts](../methodology/SERVICE.md), [examples](EXAMPLES.md),
[errors](ERRORS.md), [deployment](../operations/SERVICE.md).

Factories/lifespan own settings, PostgreSQL engines and bounded local worker threads.
Imports do not load settings or create resources. Routers validate Pydantic envelopes
and delegate blocking application work to a thread pool; financial formulas remain
in domain/application modules. CPU calculation happens after a durable job claim.

OpenAPI describes transport schemas and APIKeyHeader security. The separately exposed
/v1/workflows schemas supply exact nested command types. The service never executes
uploaded code or resolves a client type name. The unauthenticated development factory
can expose operational/schema endpoints; financial access fails closed. Production
requires explicit database and digest credentials before it can start.
