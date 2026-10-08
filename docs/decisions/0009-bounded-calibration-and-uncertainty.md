# ADR 0009 — Bounded calibration and explicit uncertainty

**Status:** Accepted; implemented in Phase 3. **Recorded:** 2026-10-01.

## Context

A numerical fit needs observations, units/provenance, parameters/bounds and meaningful
failure evidence. Successful optimization cannot be equated with a well-identified
model. Curve fitting alone cannot calibrate Hull–White volatility parameters.

## Decision

Immutable domain objectives predict sourced discount bonds, bond calls or European
calls; strict discriminated Pydantic input maps to those values. An application solver
port injects the infrastructure SciPy TRF least-squares adapter with linear loss,
three-point Jacobian and explicit scales/bounds/tolerances. Preserve signed residuals,
predictions, raw/scaled RMSE, status/message/counts/bounds, input/configuration hashes,
CalibrationRunId and model version. Non-convergence returns FAILED; model evaluation
errors raise CalibrationError with cause. No data deletion, penalty substitute or restart.

Estimate local covariance by full-rank Jacobian SVD only for converged interior
fits with residual degrees of freedom and adequate conditioning. Otherwise report
absence and reason. Covariance is an iid-scaled-residual local approximation.

## Alternatives considered

Unbounded optimization can visit invalid models. Silent convergence retries disguise
the original run. Pseudoinverse uncertainty disguises nonidentification. Global search,
robust loss and bootstrap uncertainty need explicit objectives and future validation.

## Why this decision

The workflow records what fitted, why it stopped and what uncertainty can support.
Parameter recovery tests exercise actual instrument pricing and SciPy optimization.

## Consequences

Fits are usable without APIs/database and reproducible with identical inputs/settings
on the same numerical environment. Solver settings and numerical routines are explicit.
SciPy type stubs are development-only dependencies to preserve strict core typing.

## Risks

Local minima, scale choice, finite-difference sensitivity and correlated quote errors
can mislead inference. Synthetic exact-data errors are not market confidence intervals.
The quadrature gate is independent of optimizer convergence; evaluation failures remain visible.

## Follow-up

Later authorized phases may add uncertainty propagation/governance/persistence and
financial service jobs. No calibration approval or production-market claim is made.

## Related code

`src/parallax_risk/domain/calibration/contracts.py`,
`src/parallax_risk/domain/calibration/problems.py`,
`src/parallax_risk/application/calibration.py`,
`src/parallax_risk/application/calibration_inputs.py`,
`src/parallax_risk/infrastructure/calibration/scipy_solver.py`.
`tests/quantitative/test_calibration.py`, `tests/unit/test_calibration_guards.py`,
`tests/integration/test_calibration_workflow.py`.
[Methodology](../methodology/CALIBRATION.md), [workflow](../workflows/CALIBRATION_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; calibration NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; deterministic bounded bootstrap is a separate algorithm | [Phase 2](../validation/phase-2.md) |
| 3 | Bounded sourced-instrument fits, convergence/failure and uncertainty evidence introduced | [Phase 3](../validation/phase-3.md) |
| 4 | Reviewed; calibration model 0.3.0, local optimizer and uncertainty assumptions unchanged; no implicit parameter transfer | [Phase 4](../validation/phase-4.md) |
| 5 | Reviewed; no change; Phase 5 deterministic portfolios retain this accepted contract | [Phase 5](../validation/phase-5.md) |
| 6 | Reviewed; no change; reused existing contract in Phase 6 | [Phase 6](../validation/phase-6.md) |
