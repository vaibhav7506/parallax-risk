# Service errors

Errors have application/problem+json with type=about:blank, title, status, a fixed detail
code, instance=urn:uuid:correlation and correlation_id. X-Request-ID also carries that
UUID. Responses use no-store and nosniff. Input values, connection URLs and secrets do
not appear in errors or structured logs. [Contracts](../methodology/SERVICE.md).

| Status | Meaning |
|---|---|
| 400 | Invalid JSON/duplicate keys/correlation/structural format |
| 401 | Missing or invalid opaque credential |
| 403 | Role, computed-lineage write, authority or TLS transport violation |
| 404 | Unknown resource or no owned object/job |
| 409 | Idempotency/revision/immutable identity conflict or result not available |
| 413 | Actual streamed body exceeds byte limit |
| 415 | Non-JSON media type or compressed request |
| 422 | Pydantic envelope/economic validation or work admission rejected |
| 429 | Principal rate/active-principal/global pending-job admission limit |
| 500 | Sanitized unexpected service failure |
| 503 | Missing/unavailable service dependency |

A worker error is recorded under a failed run as calculation_rejected or
internal_calculation_failure. Uncertain persistence halts its worker and retains the
running claim for inspection, rather than upgrading it to success or automatically
retrying. The operator_abandoned code marks an explicit owned abandonment.
