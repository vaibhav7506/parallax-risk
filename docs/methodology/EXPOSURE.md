# Pathwise exposure and empirical risk profiles

Phase 6 implements future repricing through the existing production pricing and
portfolio services. Positive risk is a receivable magnitude; ENE is a nonnegative
payable magnitude, not a signed accounting NPV. All outputs use the book reporting
currency in unrounded currency units and checked binary64 statistics.

## Markets known at each date

`src/parallax_risk/domain/exposure/markets.py` constructs conditional discount curves
from Vasicek or HullWhite state using their analytical bond formulas. Exact ACT/365F
civil-date offsets must equal the simulation grid. Curves use caller-supplied knots,
log-linear discounts between knots and no extrapolation. Include payment/accrual
endpoints as knots when an exact conditional bond value is required. Projection
indices share the explicitly bound currency curve: this is a single-curve assumption.
GBM FX states are QUOTE/BASE with same-day settlement. Rates and FX bindings require
explicit Q labels and units. A Q label or correlated drivers alone do not establish
consistent multi-currency martingale dynamics; stochastic-rate FX drift consistency
remains the caller's responsibility. The example uses equal deterministic rates and
zero FX drift, so that assumption is explicit and internally consistent.

Origin and earlier fixings must be supplied with eligible provenance. A future fixing
inside the horizon must be on the grid. Generate its simple forward rate at that date,
then retain it unchanged in that path's later snapshots. Future states cannot alter a
known fixing. Derived observations carry model-derived source and synthetic/sample
labels; they are not claimed to be observed vendor data. Inactive origin trades do
not request future fixing generation. Conflicting tenor/day-count specifications for
the same currency/index/date are rejected.

## Netting and collateral

For each path/date, value lifecycle-eligible positions, apply legal netting and
collateral per set, then sum positive and negative magnitudes across sets and entities.
There is no cross-entity netting. Each path owns a separate immutable ledger history.
Phase 6 provides an explicit perfect-settlement policy: automated cash equals the
full effective call only in the CSA currency with zero haircut. Daily calendar grids
are mandatory for margined books, including non-call dates. Settled cash offsets
exposure; pending calls affect instructions only. Zero-lag calls settle before that
date's published profile. Existing opening/past settled cash can use Phase 5 eligibility
and FX conventions. Pending/future initial calls are rejected. Generated movement IDs
use `sim-{step}`; caller-supplied historical IDs must not collide.

This policy does not model failed settlement, funding, collateral interest, disputes,
segregated IM or business calendars. The Phase 5 standalone frozen MPOR calculation
remains separate; it is not silently attached to pathwise default summaries.

## Statistics

For N equally weighted paths and grid time t_j, define E+ as each path's sum of
set-level positive collateral residuals and E- as its negative magnitude.
EE_j = sum(E+_i,j)/N and ENE_j = sum(E-_i,j)/N, including zero paths.
EPE is the trapezoidal integral of EE divided by the full supplied positive horizon.
It is not effective EPE. PFE(q,t_j) is NumPy's `linear` empirical quantile of E+,
with immutable strictly increasing configurable q in [0,1]. Retain the actual paths
for exact sample quantiles; no approximate streaming estimator is substituted.

Total PFE is the quantile of each path's sum of legal-scope risks, not a sum of
counterparty quantiles. PFE is nondecreasing in q; receiving more eligible collateral
can reduce positive exposure under the declared fixed valuation. Neither EE nor PFE
must increase with time: maturity can reduce them to zero. No confidence interval,
IID inference, regulatory alpha multiplier or one-year effective EPE is reported.

## EAD representation

`src/parallax_risk/domain/exposure/statistics.py` maps a finite default tau to the
first supplied grid endpoint >= tau. Values are undiscounted positive exposure at
that endpoint, including its alive-path collateral. Nondefaults contribute zero to
the unconditional mean; the conditional mean is None if no path defaults. This is
`right_grid_endpoint_no_default_conditioned_margin_freeze`: no interpolation at tau,
freeze of future calls/settlement at default or MPOR closeout is included. Coarse grids
can materially bias it, especially at maturity. Grid refinement is caller analysis.
It is not regulatory EAD, a default loss, CVA or a legal closeout estimate.

## Verification and location

`src/parallax_risk/application/exposure.py` owns the injected workflow; domain owns
markets and statistics. `tests/quantitative/test_credit_exposure.py` uses hand targets
and 60 generated PFE/collateral monotonicity cases. The workflow test compares actual
future FX-forward EE with its lognormal positive-part analytical expectation using
six sample standard errors over 2,048 paths. Conditional HullWhite knots use relative
1e-14; hazard identities use 1e-15. See [workflow](../workflows/EXPOSURE_WORKFLOW.md),
[credit](CREDIT_DEFAULT.md), [WWR](WRONG_WAY_RISK.md), and [Phase 6 evidence](../validation/phase-6.md).
