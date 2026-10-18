# Controlled quantitative mutations

**Status:** Accepted; Phase 10 implemented and verified.

## Context

A count of killed mutants can look convincing even when the baseline already fails,
inputs make a fault equivalent, or faults leak into production behavior.

## Decision

Keep typed immutable fault declarations and inject isolated mutant evaluation through
an application port. Require actual baseline and mutant checks with stable schemas;
a detection is a newly failed baseline-passing check. Retain all misses in executed
counts and rates. Abort on evaluation errors instead of counting them as detections.
Provide 15 labelled synthetic operation seams, independently targeted, and a weak
suite that exposes misses. These probes are not whole-engine AST/source mutation.

## Alternatives considered

Global patching, unbounded search, automatic repair and causal labels unsupported by
actual evidence were rejected. Explicit injected workflows retain reviewable results.

## Consequences

Research is reproducible with retained actual cases/implementations and declared
budgets, units and tolerances. Reports are immutable and serializable without I/O
or runtime initialization in the domain. No future governance workflow is scaffolded.

## Risks

Equivalent/unexercised faults and an incomplete case/suite set limit any rate.
Cash/MPOR restrictions, dated calibration-selection and sample-count probes do not
implement missing financial economics. Complete inputs and check implementations
must accompany hashes. A 100% rate on selected probes is not broad model approval.

## Related code

- `src/parallax_risk/domain/validation/mutation.py`
- `src/parallax_risk/application/validation_mutation.py`
- `src/parallax_risk/application/validation_probes.py`
- `tests/quantitative/test_adversarial_lab.py`

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
