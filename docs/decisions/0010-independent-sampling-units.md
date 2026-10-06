# ADR 0010 — Independent sampling units and pilot control variates

**Status:** Accepted; implemented in Phase 4. **Recorded:** 2026-10-01.

## Context

Dependent points can give a plausible but invalid IID standard error. Estimating
a control coefficient from the same finite evaluation sample also changes inference.

## Decision

Use ordinary paths, adjacent antithetic pair averages, or independent scramble means
as explicitly identified sampling units. Use centered streaming moments and approximate
Student t intervals. A single Sobol design has no IID interval. Require a separate
addressed pilot for control coefficients and an explicit known control expectation.
Report raw path moments separately, pilot work, convergence references, descriptive
RMSE slopes and absence reasons. Do not combine Sobol and antithetics in this release.

## Alternatives considered

IID intervals on every generated path understate or misstate dependence. Same-sample
regression is convenient but needs different finite-sample analysis. Cross-fitting,
multiple controls and bootstrap intervals add mechanisms requiring later validation.

## Consequences

The inference object reports independent unit count and total path count. Small
samples, fixed-model assumptions, quadrature bias and pilot uncertainty remain visible.
Variance reduction is measured for the chosen statistic rather than assumed.

## Risks

Student intervals are approximations outside normal settings. Caller-supplied control
expectations or sampling-unit labels can be wrong. Separate addresses cannot detect
mislabelled reused data. Intervals exclude model/discretization/finite-bit bias.

## Related code

`src/parallax_risk/domain/simulation/statistics.py`,
`src/parallax_risk/domain/simulation/controls.py`,
`src/parallax_risk/application/simulation.py`,
`src/parallax_risk/application/simulation_research.py`,
`tests/unit/test_simulation_statistics.py`.
[Statistics](../methodology/MONTE_CARLO_STATISTICS.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; simulation NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; simulation NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; simulation NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Explicit independent sampling units, absent single-design Sobol inference, separate pilot controls and work comparisons introduced | [Phase 4](../validation/phase-4.md) |
