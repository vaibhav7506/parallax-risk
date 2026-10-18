# Implemented service endpoints

Release 0.12.0. See [contracts](../methodology/SERVICE.md) and [examples](EXAMPLES.md).
Operational GET /health, /ready and /version remain public. Readiness requires live
PostgreSQL, Alembic revision 0012 when the financial service is configured, and healthy
workers. /version reports phase 12. /docs and /openapi.json document transport schemas.

All /v1 routes require X-API-Key. POST bodies require application/json with no compression.
X-Request-ID is an optional canonical UUID; a generated UUID is returned when absent.
Long calculations return 202 immediately and require Idempotency-Key.

| Method and path | Result |
|---|---|
| GET /v1/me | Authenticated subject and explicit roles |
| GET /v1/workflows | Exact nominal command JSON schemas |
| POST /v1/market/snapshots, /portfolios, /counterparties, /netting-sets, /csas, /market/scenarios, /market/pricing-contexts | Immutable owned ingestion; 201 |
| GET the same resource paths | Brief pages using after/limit |
| GET the same paths followed by /{key} | Owned exact value and digest |
| GET /v1/portfolios/{key}/counterparties, /netting-sets, /csas | Actual components of registered book |
| POST /v1/market/curves, /market/calibrations | Bootstrap/calibration jobs |
| POST /v1/pricing/trades, /pricing/portfolios | Deterministic valuation jobs |
| POST /v1/simulation | Correlated simulation statistics/diagnostics job |
| POST /v1/exposure | EE/ENE/EPE/PFE profiles and EAD research job |
| POST /v1/xva | Actual CVA/DVA/FVA/MVA research job |
| POST /v1/capital | Standardized CCR prototype/IMM challenger comparison job |
| POST /v1/validation/comparison, /convergence, /invariants, /sensitivity, /stress, /uncertainty, /mutation, /adversarial | Actual selected lab job |
| GET /v1/runs | Owned brief pages |
| GET /v1/runs/{key} | Status, safe failure code and result digest |
| GET /v1/runs/{key}/input, /result | Retained request / successful result and lineage reference |
| POST /v1/runs/{key}/abandon | Operator-owned pending job becomes failed; no compute interruption |
| POST /v1/governance | Codec schema-1 record plus expected revision/reason; role-specific write |
| GET /v1/governance/{kind}, /{kind}/{key} | Shared research inventory pages/current audited record |
| POST /v1/reports | Build immutable report from compatible retained evidence; 201 |
| GET /v1/reports, /reports/{key}, /reports/{key}/html | Owned pages/JSON/escaped CSP HTML |

Governance kinds: model, version, finding, approval, limitation, lineage, policy,
evaluation and alert. Clients cannot create lineage directly. All results use a `data`
envelope; values may contain nominal `__type__` metadata. Calculation inputs are
model_id, version_id, is_synthetic, payload and optional calibration_job. Exact financial
payload fields are documented by /v1/workflows; all economic inputs remain explicit.

`src/parallax_risk/api/routes.py` composes routes; `src/parallax_risk/application/service.py`
owns authorization/retention and `src/parallax_risk/application/workflows.py` owns engine
dispatch. [Errors](ERRORS.md), [verification](../validation/phase-12.md).
