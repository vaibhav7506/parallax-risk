# ADR 0012 — Immutable legal portfolio scopes and end-of-day lifecycle

**Status:** Accepted; implemented in Phase 5. **Recorded:** 2026-10-01.

## Context

Trade-level prices do not establish legal rights to offset claims. Forward-start
contracts can be valuable before effective date, and collateral must not leak
between separate entities or agreements. Book identity requires full content lineage.

## Decision

Use immutable PortfolioSnapshot → Counterparty → NettingSet → Trade values, with
typed unique IDs, caller-attested legal reference/enforceability and sorted tuple
content hashes. Wrap existing instruments and signed Decimal positions. Use
booking-to-final-payment/termination end-of-day eligibility; effective date is
metadata. Price only active trades via an injected deterministic port and verify
result evidence. Compute risks within sets; sum positive/negative magnitudes across
sets and counterparties in declared reporting currency without new netting.

## Alternatives considered

Flattening the book loses legal scope. Inferring enforceability from counterparties
would invent legal facts. Effective-date activation would omit forward-start NPV.
Position netting across sets would understate current claims. Mutable book lists
would invalidate hash lineage and replay.

## Consequences

CSA requires enforceable netting and set-currency agreement amounts. Negative set
values cannot cancel another set's positive risk. Future-dated booked trades are
rejected. Termination cash/partial lifecycle changes require explicit replacement
contracts or separate booked payments. No persistent version counter is inferred.

## Risks

Enforceability is caller attestation, not a jurisdictional legal opinion. End-of-day
cutoff omits intraday sequencing. Whole-trade termination does not automatically
settle or novate cash flows. Supported contracts remain the Phase 2 contract set.
No pathwise repricing, default/CVA or governance approval is implemented.

## Related code

`src/parallax_risk/domain/portfolio/contracts.py`,
`src/parallax_risk/domain/portfolio/netting.py`,
`src/parallax_risk/application/portfolio.py`,
`tests/integration/test_portfolio_workflow.py`.
[Methodology](../methodology/PORTFOLIO_COLLATERAL.md),
[workflow](../workflows/PORTFOLIO_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; portfolio NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Instrument prices supply a foundation; portfolio NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; portfolio NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; portfolio NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Immutable book, legal scopes, lifecycle and injected valuation introduced | [Phase 5](../validation/phase-5.md) |
