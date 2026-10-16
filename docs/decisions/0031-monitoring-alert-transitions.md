# ADR 0031 — Comparable monitoring and alert transitions

**Status:** Accepted; implemented and verified in Phase 11. **Recorded:** 2026-10-02.

## Context
Parameter values, calibration errors, exposure quantiles and signed XVA values have
different units and meanings. A monitoring record must state the comparison scope,
threshold and direction before a movement can justify an alert or its resolution.

## Decision
Use immutable policies and scalar evidence-linked observations for seven monitoring categories. Require identical metric/unit/comparison scope and increasing UTC observations. Evaluate explicitly absolute change, signed increase/decrease or level using strict threshold exceedance. Count failures are nonnegative integer levels. Create alerts only from registered breached evaluations; acknowledge before resolving against later comparable recovery under the same policy.

## Alternatives considered
One universal relative-change rule fails for zero baselines and obscures signed CVA
costs. Automatically aggregating vectors or inferring comparison scopes introduces
unstated policy. Clearing an alert by changing its status alone loses recovery
evidence. Explicit scalar statistics and a later comparable evaluation keep those
decisions reviewable; scheduling and notification delivery remain future work.

## Consequences
The implemented workflow requires explicit inputs, injected resources and reproducible retained evidence. See [contracts](../methodology/GOVERNANCE.md) and [workflow](../workflows/GOVERNANCE_WORKFLOW.md).

## Risks
Thresholds and scope definitions are caller policy. Negative CVA costs require declared direction. No hidden relative normalization, vector aggregation, scheduling, external delivery or automatic remediation exists. New breaches create new alerts; recovery does not prove model correctness.

## Related code
`src/parallax_risk/domain/governance/monitoring.py`, `tests/unit/test_governance.py`, `tests/integration/test_governance_postgres.py`.

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
| 9 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 9](../validation/phase-9.md) |
| 10 | Not applicable; NOT IMPLEMENTED in this phase | [Phase 10](../validation/phase-10.md) |
| 11 | Introduced; reviewed and verified on Windows/installed-wheel Linux with live PostgreSQL | [Phase 11](../validation/phase-11.md) |
