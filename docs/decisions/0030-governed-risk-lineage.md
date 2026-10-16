# ADR 0030 — Governed risk-run lineage

**Status:** Accepted; implemented and verified in Phase 11. **Recorded:** 2026-10-02.

## Context
Existing numerical engines return reproducible research results without registering
a governed risk run. Phase 11 needs a clear point at which a computed XVA result
becomes an auditable run tied to inventory and an immutable model version.

## Decision
Persist immutable Lineage for every successfully returned GovernedXva run, using actual exposure/XVA engines and registered versions. Capture actual portfolio/market/configuration/result identities, sequences including credit addresses, CSA hashes, UTC time and real environment. Optional caller revision/calibration references remain null when absent with explicit assumptions. Legacy numerical library calls remain ungoverned experiments; they do not become persisted risk jobs implicitly.

## Alternatives considered
Writing lineage after returning a result permits a successful run without committed
evidence. Intercepting every low-level pricing or simulation call would introduce
database availability into numerical experiments. The explicit injected GovernedXva
workflow commits lineage before returning while preserving those library workflows.

## Consequences
The implemented workflow requires explicit inputs, injected resources and reproducible retained evidence. See [contracts](../methodology/GOVERNANCE.md) and [workflow](../workflows/GOVERNANCE_WORKFLOW.md).

## Risks
Fingerprints do not retain input bytes. Code reference/calibration identifiers are caller declarations; there is no external calibration store or authenticated revision. Persistence can fail after numerical computation, preventing governed success. No HTTP job or broad interception is implemented.

## Related code
`src/parallax_risk/application/governed_risk.py`, `tests/unit/test_governance.py`, `tests/integration/test_governance_postgres.py`.

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
