# Actual simulation IMM challenger

Phase 8 `src/parallax_risk/domain/ccr/challenger.py` consumes empirical EE from
the actual Phase 6 pathwise repricing workflow. `src/parallax_risk/application/ccr.py`
runs that workflow separately for every legal calculation unit. Counterparty
aggregation never substitutes for a legal netting-set profile.

For EE_i at times t_i, effective EE_0=EE_0 and effective EE_i is the running
maximum through i. Let H=min(1 year, longest active contractual payment maturity)
using ACT/365F from the book origin. H must be an exact supplied grid node.
Keep nodes through H; require finite nonnegative aligned EE and a positive path count.
The research averages are sum(EE_i*(t_i-t_(i-1))/H) and
sum(effectiveEE_i*(t_i-t_(i-1))/H), for i>0. Challenger EAD is explicit
challenger alpha times effective EPE. Origin EE therefore affects the running max,
while raw right-endpoint EPE does not separately weight the origin. After contractual
maturity, EE can be zero while effective EE retains its earlier maximum.

The horizon, running-max concept and alpha structure are referenced to
[Basel CRE53.11–14](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/53/inforce/2023-01-01/published/2020-06-05).
The short-horizon normalization and right-endpoint grid quadrature above are
explicit prototype conventions. The existing Phase 6 trapezoidal full-horizon
EPE field is not substituted for this calculation.

The result retains selected EE/effective EE/times, normalized averages, alpha,
path count and an EE-projection hash. The enclosing application retains full
simulation-request/conditional-market/book/account and positive-path evidence.
The projection hash identifies EE inputs, not all empirical PFE/ENE diagnostics.
Configuration and source labels are immutable and content-addressed.

## Assumptions and limits

Actual Q paths are research scenarios with caller-supplied parameters. They are
not current/stressed approved IMM calibrations, supervisory approval or a
validated P-measure forecast. No stress maximum, downturn calibration, specific
WWR capital adjustment, rollover model, effective regulatory maturity, collateral
eligibility determination, default-conditioned margin freeze or regulatory MPOR
closeout is implemented. The underlying exposure workflow preserves all Phase 6
pricing/fixing/cash/grid limitations. Exact replay is not accuracy evidence.

Memory is bounded per calculation unit; units replay serially with common stream
addresses. Runtime grows with units. Aggregate EAD adds unit EADs without offsets.
There is no portfolio governance/lab approval, persisted risk job or financial API.

`tests/quantitative/test_ccr.py` independently verifies running maxima, unequal
interval weights, short-horizon normalization, long-grid truncation and deterministic
Monte Carlo FX values. `tests/integration/test_ccr_workflow.py` checks distinct
legal sets, individual trades, batch replay, actual margin paths and stale adapter
evidence. Monetary targets use explicit absolute tolerances and rel=0.

[Exposure](EXPOSURE.md), [standardized](STANDARDIZED_CCR.md),
[comparison](CCR_COMPARISON.md), [Phase 8 evidence](../validation/phase-8.md).

Phase 8 mapping rejects scheduled future termination/reset contracts. The
explicit MPOR must meet the configured business-day floor. The application
checks simulation-request metadata, dates, profile units/path count and path shape
in addition to book/run/market/account evidence; each scope retains runtime
simulation metadata for replay.
