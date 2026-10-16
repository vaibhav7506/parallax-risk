# Troubleshooting

| Symptom | Check / meaning | Action |
|---|---|---|
| Import/package version mismatch | Wrong environment or stale editable metadata | Use project venv, reinstall `--no-deps -e .`, compare CLI/package/pyproject version |
| Invalid configuration | Unknown PARALLAX variable, non-ASCII integer, invalid URL or production without DB | Inspect safe config and supported variable table; never print credential-bearing URL |
| Health 200 / ready 503 | Process exists but probe not started/configured or DB unavailable | Check configured host/network and database health; readiness is deliberately not fake success |
| DB test skipped | PARALLAX_TEST_DATABASE_URL absent | Supply isolated live DB URL; don't report this as successful live integration |
| Port 8000 busy | Another workload may own it | Use verification override 58000/55432; do not stop other projects |
| Missing fixing/curve/direct FX | Required explicit input absent | Provide exact known fixing/index assignment/pair; no hidden inverse/projection fallback |
| Curve horizon/bootstrap failure | Unsupported date/extrapolation or bracket/convergence/repricing gate | Review declared nodes/settings/quote conventions; don't widen or repair silently |
| NumericalError | Nonfinite/overflow/underflow or inexact primitive Money operation | Review units/ranges/precision and assumptions; never replace with zero or clipped output |
| Sensitivity bump rejected | Nonpositive FX quote or bump below binary64 resolution | Choose/document a meaningful bump and compare stability; preserve base/up/down evidence |
| Cleanup ownership mismatch | Candidate belongs to another workspace or has unowned users | Retain and inspect; do not bypass guard or global-prune |
| Calibration FAILED | Optimizer reached its budget or did not meet termination | Preserve result, inspect residuals/bounds/message; no automatic restart or success upgrade |
| Missing covariance | Active bounds, failed fit, insufficient rank/DOF or poor condition | Read unavailable_reason; do not fabricate confidence intervals |
| Heston integration failure | Infinite quadrature convergence/error/arbitrage gate failed | Preserve settings/parameters; explicitly revise tolerances/domain if justified; no clipping |
| Cholesky rejected | Singular or numerically unresolved dependence | Inspect eigenvalues/order; repair requires separate explicit request/report |

Relevant code: common/errors, application/config, domain/market/curves, domain/pricing
and infrastructure/persistence. Their authored messages avoid revealing DB details.
Save safe logs/input hashes and reproduce with the [replay guide](../REPRODUCIBILITY.md).

Docker engine/configuration failure is a prerequisite problem, not proof of a pricing
defect. Start Docker through the user's normal installation if needed; do not reset
the engine or delete other workloads. Existing TestClient deprecation is documented
and does not imply a new financial model failure.

For Phase 4, odd antithetic counts split independent pairs and are rejected. Sobol
requires power-of-two complete designs/batches and a supported step/driver dimension.
A single Sobol design's missing IID interval is deliberate: use independent scramblings.
Exact Heston requests and singular correlation factorization fail without fallbacks.
Use `python scripts/execute_notebooks.py` in the locked development interpreter if a
notebook kernel imports a different package/environment.

For Phase 5, verify matching end-of-day market/book dates, one uniquely identified
ledger per CSA scope, direct FX orientation and curve horizon, movement schedule/lag,
eligible currencies and one-way holding direction. Pending calls do not offset current
risk; MTA equality intentionally produces zero transfer. See
[portfolio conventions](../methodology/PORTFOLIO_COLLATERAL.md).

Phase 6: For exposure failures, check exact ACT/365F grid alignment, Q bindings/units, sufficient knots, origin fixing provenance and future fixing grid membership. Margined paths need daily calendar grids, one scoped account and zero-haircut CSA cash. Credit needs aligned horizons and unique addresses. Do not fix invalid data by implicit repair.
See [workflow](../workflows/EXPOSURE_WORKFLOW.md) and [limits](../LIMITATIONS.md).

Phase 7: check exact exposure/credit/run identities, one ordered IM profile per name,
same currency/origin/ACT365F grid and all finite curve horizons. Verify component signs
and -FCA+FBA reconciliation. Central differences require admissible resolved +/-h;
unsupported policy/volatility/shared-spread or PSD failures must not be silently
repaired. [Risk conventions](../methodology/XVA_SENSITIVITIES.md).

CCR rejects missing exact first-year/final-maturity grid nodes, unsupported
instruments/foreign reporting sets, stale simulation evidence, missing/duplicate
CSA ledgers or explicit margin specifications, non-daily/post-only CSA and
mismatched TH/MTA. Correct the source input; do not pad grids, replace weights,
repair legal scope or convert calendar MPOR automatically.
[Supported workflow](../workflows/CCR_WORKFLOW.md).

## Phase 9 lab scope

A failed validation finding is a retained outcome, not necessarily a software defect. Inspect units, benchmark assumptions, tolerances, grid bias and sampling precision. Single Sobol path inference, unsupported dependent CVA observations, unavailable/constrained covariance, non-PSD covariance and inadmissible stresses reject explicitly.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 applicability

A callback economic rejection aborts optimization explicitly and preserves its actual error. Empty feasible populations, stale case evidence, changing units/model schemas and budget overruns are errors. A miss or false convergence flag is retained evidence, not automatically an execution error.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).

## Phase 11 applicability

Missing revision 0011 requires an explicit migration on the correctly selected
schema; SELECT 1 readiness does not prove schema readiness. Stale revision or
reference means reread/review, never blind overwrite/retry. Duplicate synthetic
demo IDs require a fresh isolated schema. Invalid recovery evidence cannot resolve
an alert. Digest/identity mismatch on read is a failure, not automatic repair.
Docker startup failure does not establish a test result or safe cleanup inventory.

[Governance contracts](../methodology/GOVERNANCE.md), [actual phase evidence](../validation/phase-11.md).
