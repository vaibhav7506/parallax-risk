# ADR 0015 — Finite-horizon credit and explicit dependence policies

**Status:** Accepted; implemented and verified in Phase 6. **Recorded:** 2026-10-01.

## Context

Exposure/default dependence cannot be inferred from unconditional EE or a root seed alone.

## Decision

Supply immutable nonnegative piecewise hazards and constant recovery. Own independently addressed positive exponential thresholds. Declare independent deterministic, marginal-preserving full-path static rank stress, or adapted left-grid spread intensity. Report baseline and scenario survival separately.

## Alternatives considered

Silent calibration or hazard repair changes supplied assumptions. Static ranking cannot be relabelled a causal hazard. Stochastic intensity does not automatically match deterministic marginal survival.

## Consequences

Default inversion includes the final endpoint; no in-horizon default is None. ReducedFormSpread uses the declared credit-triangle approximation s/(1-R). Policy hashes include injected spread semantics.

## Risks

Finite-grid intensity bias, non-adapted static stress and uncalibrated dynamic marginals remain explicit. Recovery is not applied to Phase 6 exposure. No CDS calibration, CVA or bilateral default pricing exists.

## Related code

`src/parallax_risk/domain/credit/hazard.py`, `src/parallax_risk/domain/credit/dependence.py`, `src/parallax_risk/domain/exposure/contracts.py`, `tests/quantitative/test_credit_exposure.py`.
[Methodology](../methodology/EXPOSURE.md), [credit/WWR](../methodology/WRONG_WAY_RISK.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 6 pathwise exposure/credit NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Introduced explicit policy and implementation; verified on both platforms | [Phase 6](../validation/phase-6.md) |
