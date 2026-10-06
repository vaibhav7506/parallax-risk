# Operational API philosophy and scope

The FastAPI factory exposes process/dependency/release information only. Quantitative
workflows are Python library calls today; no POST pricing/simulation/exposure/XVA
endpoint exists. Keep financial formulas in domain, never route handlers.

`src/parallax_risk/api/app.py` (`create_app`) explicitly loads settings at invocation,
owns the injected/lazy probe's lifespan and checks synchronous DB work in a thread
pool. Package import starts no service. API release metadata follows the package.

Versioned financial endpoints, authentication, request correlation IDs, idempotency
keys, long-running risk jobs and pagination are NOT IMPLEMENTED / Phase 12 planned.
Current GET operations have no mutation body or job state. Generated OpenAPI/docs
are useful schema views but not a financial API contract or security layer.

Read [endpoints](ENDPOINTS.md), [errors](ERRORS.md), [examples](EXAMPLES.md) and
[security scope](../../SECURITY.md). Bind locally; no enterprise-service claim is made.

Phase 4 adds an injected Python simulation research workflow and executed notebooks.
It adds no financial HTTP route or asynchronous risk-job lifecycle. Operational version
metadata advances to release 0.4.0 and phase 4.
