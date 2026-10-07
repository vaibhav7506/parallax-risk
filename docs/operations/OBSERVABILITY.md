# Logs and health

`src/parallax_risk/common/logging.py` creates instance-local structlog loggers without
global configuration. The envelope contains event, level/time and optional run ID,
outcome and safe error type. There is no raw portfolio/market/credential field.

PricingService emits pricing_started/completed/failed, correlating by RunContext ID
and propagating authored domain/numerical errors. Demo logs use stderr; computed
result JSON uses stdout. Log timestamps vary even when deterministic result metadata
is fixed. API lifecycle emits service_started/stopped and dependency-check outcomes.

`/health` is process liveness, `/ready` checks startup/configured real PostgreSQL and
`/version` reports release/phase. No metrics dashboard, distributed tracing, request-ID
middleware, model monitoring or persisted audit stream is implemented.
See [API](../api/ENDPOINTS.md) and [reproducibility](../REPRODUCIBILITY.md).

Phase 4 simulation logs use only the restricted start/completed/failed envelope with
run ID, outcome and error type. Numerical values, observable outputs, curves and
control coefficients are kept in explicit research results, not workflow logs.

Phase 5 portfolio logs use the same restricted start/completed/failed envelope.
Only run ID, outcome and authored error type are logged, never trades, collateral
amounts, legal references or credential-bearing market inputs.
