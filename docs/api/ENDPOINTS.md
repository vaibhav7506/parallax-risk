# Implemented endpoints

| Method/path | Success response | Failure semantics |
|---|---|---|
| GET /health | 200 `{"status":"ok"}` | Liveness only; DB availability not checked |
| GET /ready | 200 `{"status":"ready","database":"connected"}` | 503 not_ready with database unavailable/not_configured before startup or dependency failure |
| GET /version | 200 `{"name":"Parallax Risk","version":"0.3.0","phase":3}` | Metadata endpoint, no financial calculation |

Implementation: `src/parallax_risk/api/app.py` and `src/parallax_risk/api/schemas.py`.
`tests/api/test_operations.py` validates injected-probe/lifecycle/response behavior.
Examples are expected schema examples, not a claim a server is currently running.

No authenticated financial endpoint, upload, risk-job resource, request-ID header or
pagination contract exists. Update these documents with actual new behavior only
in its authorized phase.
