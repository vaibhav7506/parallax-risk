# Restricted SA-CCR-inspired prototype

Phase 8 implements `src/parallax_risk/domain/ccr/standardized.py` and immutable
inputs in `src/parallax_risk/domain/ccr/contracts.py`. This is a research
methodology prototype, without a regulatory-compliance claim. The supported
mapping is domestic vanilla fixed/float IRS and domestic-quote deliverable FX
forwards. Bonds, cash flows, options, credit, equity, commodities, basis and
volatility trades are rejected. Legal enforceability is caller attestation.

## Equations and units

All amounts are reporting-currency units. V is signed clean value; C is signed
settled effective collateral, positive when held. Unmargined RC=max(V-C,0).
Margined RC=max(V-C,TH+MTA-NICA,0). NICA and business-day MPOR require explicit
source-labelled inputs; they are not inferred from reusable CSA IA or calendar days.

For IR, adjusted notional is N times supervisory duration:
SD=max((exp(-b*S)-exp(-b*E))/b,10/B), evaluated with expm1 for short periods.
For FX, adjusted notional is the foreign base leg converted using explicit
same-day direct spot. Signed quantity scales absolute notional and linear delta.
PAY_FIXED is +1, RECEIVE_FIXED -1; BUY_BASE +1, SELL_BASE -1 before quantity sign.
The currency-pair key sorts currencies and reverses delta when orientation reverses.

Unmargined MF=sqrt(min(max(M,10/B),1)); margined MF=1.5*sqrt(MPOR/B).
Effective notional is adjusted notional * MF * delta. IR groups use currency and
E<1, 1<=E<=5, E>5 buckets. Sum absolute bucket totals; recognize no cross-bucket
offset. FX uses absolute currency-pair totals. Sum all group add-ons, without
cross-currency/pair/asset diversification. Defaults: b=.05, B=250, IR SF=.005,
FX SF=.04; explicit configuration may change these research assumptions.

For A=aggregate add-on and f=.05, multiplier=min(1,f+(1-f)*exp((V-C)/(2*(1-f)*A))).
PFE=multiplier*A; EAD=alpha*(RC+PFE), default alpha=1.4. A=0 yields PFE=0 and
reported multiplier=1. Margined EAD is capped by a second unmargined calculation
with identical V/C/trades. Both uncapped EAD and cap remain visible.

These formula references and the no-cross-bucket-offset option are documented in
[Basel CRE52, effective 2023-01-01, updated 2020-06-05](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05).
This source/version does not establish jurisdictional eligibility or approval.

## Numerical and legal contracts

Decimal Money inputs become checked binary64 values; outputs use unrounded
shortest-round-trip Decimal spellings. Nonfinite values, conversion underflow,
overflow, malformed units and unsupported products reject. Exponential decay
rounding to zero is the mathematically defined multiplier-floor limit. The
supervisory duration and maturity floors are explicit model rules, not input repair.

Every netting unit is calculated separately. Enforceable sets permit internal
offset; non-enforceable sets become individual trade units in the application.
No counterparty, cross-set or cross-entity offset is inferred. Structured inputs
are canonicalized by trade ID; results retain hashes and every trade/group driver.

## Verification and limits

`tests/quantitative/test_ccr.py` checks independent FX/IR targets, floors,
offset boundaries, collateral, margin cap and homogeneous scaling. The two RC
targets use the numerical examples in
[Basel CRE99.98–104](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/99/inforce/2023-01-01/published/2020-03-27):
V=80m/C=90m/TH=0/MTA=1m/NICA=10m gives RC=0; C=79.5m/NICA=0 gives RC=1m.
Other tests are explicitly synthetic hand-derived fixtures, not market benchmarks.

Only daily receive-capable bilateral CSA comparisons are supported. MPOR >=10
business days is caller-supplied; dispute/large-set/illiquid floors, clearing,
multiple CSAs, segregation/legal eligibility and collateral outside scopes are
unsupported. Production research margin simulation retains its daily calendar,
perfect-settlement, same-currency zero-haircut cash and alive-path limitations.
No local transposition, full rulebook, capital treatment or legal opinion is supplied.

[Challenger](IMM_CHALLENGER.md), [comparison](CCR_COMPARISON.md),
[workflow](../workflows/CCR_WORKFLOW.md), [Phase 8 evidence](../validation/phase-8.md).

Phase 8 mapping rejects scheduled future termination/reset contracts. The
explicit MPOR must meet the configured business-day floor. The application
checks simulation-request metadata, dates, profile units/path count and path shape
in addition to book/run/market/account evidence; each scope retains runtime
simulation metadata for replay.
