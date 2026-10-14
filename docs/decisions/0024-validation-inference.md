# 0024 — Independent-unit convergence and uncertainty

**Status:** Accepted; Phase 9 implemented and verified.

## Context

Dependent points, silent covariance repair and unconditional uncertainty claims can create misleading precision.

## Decision

Reuse owned independent-unit t inference. Require valid counts, SEM and t bounds, explicit ladders/precision/stability criteria. Bootstrap independent units with owned replicate addresses; keep supplied parameter ranges distinct from covariance normal approximations. Calibration propagation requires actual admissible h/h2 repricing and available unconstrained PSD covariance.

## Alternatives

Implicit conversion, silent numerical repair and fabricated adapters were rejected.
Existing NumPy/SciPy and injected library workflows avoid required external engines.

## Consequences

Evidence is explicit and reproducible, with failures retained. No persistence or financial HTTP job is introduced.

## Risks

Finite ladder stability does not bound grid bias. Bootstrap/local-normal bands have approximate conditional interpretations; covariance may be unavailable.

## Related code

`src/parallax_risk/domain/validation/checks.py`, `src/parallax_risk/domain/validation/uncertainty.py`, `src/parallax_risk/application/validation_models.py`.

[Methodology](../methodology/MODEL_VALIDATION.md), [workflow](../workflows/VALIDATION_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 6](../validation/phase-6.md) |
| 7 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 7](../validation/phase-7.md) |
| 8 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 8](../validation/phase-8.md) |
| 9 | Introduced; implementation and explicit scope recorded | [Phase 9](../validation/phase-9.md) |

Phase 9 constructs the existing full-rank SVD covariance estimator from weighted
Gram entries, evaluating each symmetric entry once. The lab still rejects asymmetric
caller covariance exactly and never clips eigenvalues. This resolves the observed
Linux BLAS rounding asymmetry at the estimator source. The existing calibration
mathematical assumptions remain unchanged. [Phase 9 evidence](../validation/phase-9.md).
