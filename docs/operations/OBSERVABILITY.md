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

Phase 6: ExposureService uses restricted start/completed/failed events with run ID and authored error type. Per-date portfolio calls retain safe envelopes; exposure arrays/trade terms are not logged automatically.
See [workflow](../workflows/EXPOSURE_WORKFLOW.md) and [limits](../LIMITATIONS.md).

Phase 7: XvaService emits restricted started/completed/failed events with RunContext
ID and authored error type. Revaluation may emit multiple such workflows. Financial
component values, path arrays and full terms are returned to the caller, not logged
automatically. The synthetic demo explicitly owns an in-memory logger stream.

Phase 8 CcrService reuses injected portfolio/exposure workflow logs per legal unit;
there is no global logger configuration or governance monitor. The returned report
preserves scoped path/configuration evidence and comparison exception flags.
[Workflow](../workflows/CCR_WORKFLOW.md).

## Phase 9 lab scope

The lab retains check evidence/findings in its returned report. Existing exposure/XVA/calibration workflow logging remains explicitly configured. No monitoring, alert dispatch, governance approval or automatic remediation is added.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 applicability

Phase 10 emits canonical machine-readable model/fault/search/diagnostic evidence; no automatic alerts, dashboard, persisted findings or model approvals are added. Failed materiality/optimizer convergence remains visible in reports.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).

## Phase 11 applicability

Monitoring Policies/Evaluations are persisted research evidence, separate from
operational service logs. They cover seven scalar categories and retain units,
comparison scope, threshold and source hashes. Alerts follow explicit
open/acknowledged/resolved transitions backed by later recovery evidence. No
scheduled collector, external notification delivery or authenticated actor exists.

[Governance contracts](../methodology/GOVERNANCE.md), [actual phase evidence](../validation/phase-11.md).
