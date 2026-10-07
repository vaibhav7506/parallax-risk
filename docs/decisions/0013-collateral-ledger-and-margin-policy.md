# ADR 0013 — Signed collateral ledger, explicit margin policy and frozen MPOR

**Status:** Accepted; implemented in Phase 5. **Recorded:** 2026-10-01.

## Context

Unsettled calls do not extinguish current exposure, but ignoring pending calls
causes duplicates. Haircut-adjusted agreement values differ from physical cash.
Collateral timing, MTA boundary and IA rights require declared conventions.

## Decision

Store frozen opening cash balances and uniquely identified dated physical movements
per CSA/set. Positive means received, negative posted. Use settled balances for
V-C and include known pending transfers only when calculating target differences.
VM follows explicit directional thresholds; total target adds signed reusable
title-transfer IA. Use fixed calendar-day scheduling/lag/MPOR and strict-greater
MTA, transferring the full difference. Haircuts apply to signed physical balances.
Convert with direct settlement-adjusted FX and exact-contract Money multiplication
of Decimal(str(binary64 factor)). Calls are effective-value instructions; caller
allocation/confirmed cash entries remain explicit. Freeze settled physical balances
at default, revalue at the exact MPOR endpoint and ignore subsequent settlements.

## Alternatives considered

Offsetting exposure by pending calls understates settlement risk. Ignoring pending
calls double-counts requested transfers. Treating effective calls as nominal cash
ignores haircuts. Silent inverse FX/rounding would breach existing conventions.
Equating reusable IA to segregated IM invents legal availability. Inferred business
calendars and universal CSA MTA semantics would overstate the supported scope.

## Consequences

One-way accounts may return held cash but cannot finish in the opposite holding
direction. Eligibility, all settled states and movement timing are validated.
Call equality with MTA suppresses transfer. MPOR is a deterministic user scenario,
not regulatory exposure-at-default or an IM estimation method. Metadata retains
the input account and closeout market hashes; original ledgers never mutate.

## Risks

Cash only; no securities, interest, disputes, settlement failures, liquidation,
segregation or regulatory margin compliance. Haircuts use a symmetric signed-value
research convention. Direct FX requirements restrict supported conversion graphs.
Calendar-day MPOR is caller chosen. Decimal arithmetic can reject excess precision;
binary64 valuation remains approximate. See the [methodology assumptions](../methodology/PORTFOLIO_COLLATERAL.md).

## Related code

`src/parallax_risk/domain/portfolio/csa.py`,
`src/parallax_risk/domain/portfolio/collateral.py`,
`tests/quantitative/test_collateral_netting.py`.
[Workflow](../workflows/PORTFOLIO_WORKFLOW.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; collateral NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Money/FX pricing supply a foundation; collateral NOT IMPLEMENTED | [Phase 2](../validation/phase-2.md) |
| 3 | Not applicable; collateral NOT IMPLEMENTED | [Phase 3](../validation/phase-3.md) |
| 4 | Not applicable; collateral NOT IMPLEMENTED | [Phase 4](../validation/phase-4.md) |
| 5 | Pending-aware calls, explicit cash/haircut/FX and frozen MPOR introduced | [Phase 5](../validation/phase-5.md) |
