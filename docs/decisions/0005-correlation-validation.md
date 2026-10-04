# ADR 0005 — Correlation validation

**Status:** Accepted. **Implementation:** Phase 3.
**Recorded:** 2026-10-01; accepts the prior proposed policy and preserves its history.

## Context
Joint market models need coherent dependence. Invalid pairwise correlations can
create negative variance. Phase 2 had no correlation input; Phase 3 implements this
primitive before joint simulation.

## Decision
Require immutable ordered unique factors, finite aligned square input, entries in
[-1,1], exact symmetry and exact unit diagonal. No tolerance-based averaging occurs.
PSD accepts eigenvalues >=-1e-12 by default as a declared roundoff policy. Diagnostics
expose unchanged input/eigenvalues. Cholesky requires minimum eigenvalue above the
tolerance and reconstruction max-entry error within it. Singular/unresolved matrices
fail factorization explicitly; no eigenfactor fallback exists.

Provide separately requested `repair_correlation(..., requested=True)` with eigenvalue
clipping (default floor 1e-8) and diagonal rescaling. Report original matrix/hash/
eigenvalues, output matrix/hash, clipped count, floor/method and Frobenius change.
Structural/asymmetric/nonfinite defects remain rejected. This is not a nearest-matrix
optimizer. Normal model, calibration and correlation validation never call repair.

## Alternatives considered
Silent nearest-matrix projection hides changes in risk assumptions. Singular eigenfactor
simulation could support redundant factors later but needs an explicit factor policy.
Rejecting all near-zero eigenvalues would discard meaningful singular PSD input.

## Why this decision
Dependence changes must be traceable. Validation, numerical resolution and repair
are separate decisions. Exact structure avoids ambiguity about which triangle is used.

## Consequences
Singular PSD input can be represented but cannot use Cholesky. A caller must inspect
the explicitly requested repair report before using changed assumptions.

## Risks
PSD tolerance is an absolute numerical allowance, not statistical uncertainty.
Clipping changes dependence and need not minimize matrix distance.

## Follow-up
Joint path/correlation reproduction tests belong to Phase 4 and are NOT IMPLEMENTED.

## Related code
`src/parallax_risk/domain/models/correlation.py`: CorrelationMatrix, diagnostics,
CorrelationRepair and repair_correlation. `tests/unit/test_correlation.py`,
`tests/property/test_model_invariants.py`.
[Methodology](../methodology/CORRELATION.md), [Phase 3](../validation/phase-3.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; correlation NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; deterministic pricing needs no correlation | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | User-requested proposed policy recorded; no implementation phase advanced | [Register](README.md) |
| 3 | Proposal accepted: strict validation, PSD diagnostics, Cholesky and reported opt-in repair | [Phase 3](../validation/phase-3.md) |
