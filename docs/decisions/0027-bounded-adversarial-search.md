# Bounded adversarial model search

**Status:** Accepted; Phase 10 implemented and verified.

## Context

Production/challenger disagreement depends on financial inputs, finite grids and
sampling. Searching arbitrary parameter values can produce implausible conclusions.

## Decision

Inject SearchOptimizer; use SciPy differential evolution with owned PCG64DXSM,
explicit finite ordered bounds/units/rationales and aligned linear restrictions.
Maximize an actual same-case selected-metric absolute disagreement, preserve every
feasible pair, model identity, optimizer status and hard planned/actual budget.
Disable polishing/parallelism and retain best actual evidence without extra valuation.
Economic constructors reject invalid candidates without clipping/repair/penalties.
Provide independent-credit XVA CVA quadrature and ordered six-factor delta mapping;
shared exposure simulation is explicitly outside this independent challenge.

## Alternatives considered

Global patching, unbounded search, automatic repair and causal labels unsupported by
actual evidence were rejected. Explicit injected workflows retain reviewable results.

## Consequences

Research is reproducible with retained actual cases/implementations and declared
budgets, units and tolerances. Reports are immutable and serializable without I/O
or runtime initialization in the domain. No future governance workflow is scaffolded.

## Risks

Ranges are caller-declared synthetic plausibility, not authenticated market history.
Convergence is not global optimality; finite/noisy grids and optimizer selection can
exaggerate disagreement. A finite constraint search can stop short of a known optimum.
No nonlinear PSD repair, WWR quadrature, out-of-sample correction or event likelihood
is inferred. Invalid economic callbacks preserve their original failure.

## Related code

- `src/parallax_risk/domain/validation/search.py`
- `src/parallax_risk/application/validation_search.py`
- `src/parallax_risk/application/validation_search_models.py`
- `src/parallax_risk/infrastructure/validation/scipy_search.py`
- `tests/integration/test_adversarial_workflow.py`

## Phase history

| Phase | Review / change | Evidence |
|---|---|---|
| 1 | Not applicable; NOT IMPLEMENTED | Historical Phase 1 scope |
| 2 | Not applicable; NOT IMPLEMENTED | Historical Phase 2 scope |
| 3 | Not applicable; NOT IMPLEMENTED | Historical Phase 3 scope |
| 4 | Not applicable; NOT IMPLEMENTED | Historical Phase 4 scope |
| 5 | Not applicable; NOT IMPLEMENTED | Historical Phase 5 scope |
| 6 | Not applicable; NOT IMPLEMENTED | Historical Phase 6 scope |
| 7 | Not applicable; NOT IMPLEMENTED | Historical Phase 7 scope |
| 8 | Not applicable; NOT IMPLEMENTED | Historical Phase 8 scope |
| 9 | Not applicable; NOT IMPLEMENTED | Historical Phase 9 scope |
| 10 | Introduced; explicit implementation/limitations verified on both platforms | [Phase 10](../validation/phase-10.md) |
| 11 | Reviewed; no change; existing numerical contracts retained by evidence/report consumers | [Phase 11](../validation/phase-11.md) |
| 12 | Reviewed; no change; numerical/research contract remains applicable | [Phase 12](../validation/phase-12.md) |
