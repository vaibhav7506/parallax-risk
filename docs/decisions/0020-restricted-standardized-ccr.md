# 0020 — Restricted standardized CCR prototype

**Status:** Accepted. Introduced Phase 8, 2026-10-01.

## Context

The implemented pricer supports vanilla IRS and FX forwards but has no option,
credit/equity/commodity or regulatory eligibility models. A comparative prototype
must identify its supported scope and preserve financial/legal boundaries.

## Decision

Use immutable explicit currency-unit inputs and source-labelled supervisory
parameters. Map only domestic vanilla IRS and domestic-quote FX. Calculate each
legal unit separately, with within-IR-bucket and FX-pair offset, no cross-IR-bucket
offset, explicit duration/maturity floors and the margined/unmargined cap.
Require distinct business-day MPOR/NICA inputs; do not reinterpret calendar CSA IA.
Retain every trade/group driver and input hash. Name this SA-CCR-inspired research.

## Alternatives

Claiming full SA-CCR omits unsupported eligibility/product/margin rules. Mapping
all priced cash instruments as derivatives misstates scope. Cross-bucket covariance
aggregation is unnecessary for this restricted documented option and remains absent.

## Consequences

Unsupported scope rejects explicitly. No new dependency, market feed, service,
table or financial API is required. Binary64 quantitative precision remains distinct
from exact Decimal Money arithmetic. Configuration changes are caller assumptions.

## Risks

Research margin simulation is not regulatory closeout; legal attestations are not
opinions. Large-set/dispute/clearing and jurisdictional eligibility are unsupported.
No regulatory-compliance claim is made.

## Related code

`src/parallax_risk/domain/ccr/contracts.py`, `src/parallax_risk/domain/ccr/standardized.py`,
`src/parallax_risk/domain/ccr/mapping.py`, `tests/quantitative/test_ccr.py`.
[Methodology](../methodology/STANDARDIZED_CCR.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 5](../validation/phase-5.md) |
| 6 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 6](../validation/phase-6.md) |
| 7 | Not applicable; Phase 8 prototype NOT IMPLEMENTED | [Phase 7](../validation/phase-7.md) |
| 8 | Introduced restricted formulas, mapping and explicit margin assumptions; verified on both platforms | [Phase 8](../validation/phase-8.md) |
