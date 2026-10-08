# ADR 0016 — Empirical exposure, perfect cash settlement and grid EAD

**Status:** Accepted; implemented and verified in Phase 6. **Recorded:** 2026-10-01.

## Context

Portfolio paths need reproducible empirical summaries and a precise distinction between alive exposure and default closeout.

## Decision

Reprice every path/date through PortfolioService, preserve legal-scope separation, and collect positive/negative matrices under an explicit output cap. EE/ENE include zero paths; PFE is linear empirical quantile; EPE is a full-horizon trapezoidal average. Advance separate ledgers with perfect scheduled zero-haircut CSA-currency cash settlement on a daily grid. Right-grid EAD uses alive collateral and is explicitly labelled as omitting default-conditioned freeze/MPOR.

## Alternatives considered

Summing counterparty PFE is not a quantile of aggregate path risk. Implicit nominal allocation ignores haircuts. Calling alive-path exposure a regulatory EAD or MPOR closeout overstates implementation. Approximate quantile sketches are not substituted.

## Consequences

Extends Phase 5 with a restricted explicit simulator settlement policy; its generic caller-confirmed ledger and standalone frozen MPOR remain valid. Initial pending/future calls are rejected. Zero-lag settlement affects that day's exposure. No API/persistence is added.

## Risks

Output cap is not peak memory. Empirical statistics have no reported confidence interval. Right-endpoint exposure can be biased, especially near maturity. No default freeze, bilateral closeout, regulatory effective EPE/EAD, CVA or funding is implemented.

## Related code

`src/parallax_risk/application/exposure.py`, `src/parallax_risk/domain/exposure/statistics.py`, `tests/integration/test_exposure_workflow.py`.
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
