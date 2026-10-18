# Material-change forensic evidence

**Status:** Accepted; Phase 10 implemented and verified.

## Context

A material risk change may coincide with several input/configuration changes.
A numerical attribution that conceals residuals cannot establish its cause.

## Decision

Evaluate actual before/after twice plus ordered caller-supplied counterfactual cases.
Retain metric/unit-aligned outputs, context fingerprints, adapter version, separate
materiality/repeatability checks, seven possible-cause buckets and arithmetic residual.
Use explicit tolerance units. A failed materiality threshold triggers investigation;
a failed actual repeat flags numerical instability. Preserve overlapping labels and
ordered step valuations rather than claiming a causal partition or Shapley result.

## Alternatives considered

Global patching, unbounded search, automatic repair and causal labels unsupported by
actual evidence were rejected. Explicit injected workflows retain reviewable results.

## Consequences

Research is reproducible with retained actual cases/implementations and declared
budgets, units and tolerances. Reports are immutable and serializable without I/O
or runtime initialization in the domain. No future governance workflow is scaffolded.

## Risks

Fingerprint changes are evidence of changed inputs, not causal contributions.
Numerical configuration changes need convergence studies; passing repeats do not
prove accuracy. Caller calibration hashes and case labels are not authenticated.
Hashes alone do not reconstruct cases. No governance persistence or approval exists.

## Related code

- `src/parallax_risk/domain/validation/forensics.py`
- `src/parallax_risk/application/validation_forensics.py`
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
