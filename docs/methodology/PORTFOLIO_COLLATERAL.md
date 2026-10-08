# Portfolios, legal netting and cash collateral

Phase 5 adds deterministic book valuation and collateral accounting. All examples
are synthetic. No default probabilities, stochastic exposure profiles, EE/PFE or
CVA calculation is implemented. [Workflow](../workflows/PORTFOLIO_WORKFLOW.md),
[tutorial](../tutorials/04-FIRST-PORTFOLIO-RUN.md), [evidence](../validation/phase-5.md).

## Book and lifecycle

`src/parallax_risk/domain/portfolio/contracts.py` implements PortfolioSnapshot →
Counterparty → NettingSet → Trade. A Trade wraps an existing supported Instrument,
signed nonzero Decimal quantity, booking/effective dates and optional termination
date/reason. Its pricing currency follows the existing instrument NPV convention;
an FX forward also retains its original base-notional currency. Legal entity,
netting-set, trade and CSA IDs are unique throughout a portfolio snapshot.

Snapshot collections are sorted by typed ID before hashing. The digest includes
identity/version, valuation date, reporting currency, contracts, quantities,
lifecycle and legal/CSA declarations. The version is an opaque caller-supplied
token, not a monotonic counter. Creating a changed frozen value creates changed
content identity; it does not publish or persist a revision automatically.

ASSUMPTION: end-of-day valuation excludes payments/termination on the valuation
date. Booking cannot follow snapshot date. A forward-start trade has value from
booking, even before effective date. Termination excludes the whole contract;
termination/novation consideration must be booked separately. There is no automatic
partial termination, novation transfer, settlement reconciliation or legal opinion.

## Scope and signs

`src/parallax_risk/domain/portfolio/netting.py` requires exactly one signed,
quantity-adjusted Money value for every trade, with zero for inactive trades.
Values convert to the set's declared currency before addition. Let v_i be those
values. V = sum(v_i); gross positive G+ = sum(max(v_i,0)); gross negative magnitude
G- = sum(max(-v_i,0)). With caller-attested enforceable netting, positive risk is
max(V,0), and negative magnitude is max(-V,0). With netting disabled they are G+
and G-. The signed accounting value remains V in both cases.

CSA collateral is supported only within an enforceable netting set with matching
agreement/reporting currency. Each set has its own account; collateral never
spills across sets. Counterparty and portfolio positive/negative risks are sums
of separate set results after conversion, even when total signed accounting value
is negative. A +100 set and a -80 set therefore retain +100 positive risk; their
accounting value is +20. Moving both trades into one enforceable set gives +20 risk.

Received cash collateral is positive C; posted cash is negative C. Settled
collateral gives residual R = V-C, positive risk max(R,0) and negative magnitude
max(-R,0). Pending transfers do not reduce current risk. Extra received collateral
can produce a negative residual, and posted collateral can increase positive risk.
These are declared research amounts, not regulatory capital exposure measures.

## CSA target and minimum transfer

`src/parallax_risk/domain/portfolio/csa.py` owns explicit receive/post thresholds,
MTA, signed title-transfer independent amount IA, eligible cash currencies with
haircuts, direction, first margin date, frequency, settlement lag and MPOR.
Thresholds/MTA are nonnegative Money in agreement currency. Zero is meaningful.
Haircuts are Decimal h in [0,1); h=1 is rejected. All dates use civil calendar days,
including weekends; there is no inferred holiday calendar or business-day shift.

For two-way exchange, VM = max(V-TH_receive,0)-max(-V-TH_post,0). Receive-only
omits the negative term; post-only omits the positive term. Total target T = VM+IA.
IA must have the allowed direction for one-way agreements. IA here means signed,
reusable title-transfer collateral. It is not segregated regulatory initial margin;
the latter cannot be inferred from an IA number and remains unsupported.

Let C_projected include settled balances plus all calls known by valuation date
that will settle later. Difference Δ = T-C_projected. On scheduled margin dates,
transfer the full Δ only when |Δ| > MTA. Equality suppresses the call. MTA is not
deducted from an executed transfer. Reviews before the anchor or off the fixed
frequency grid issue zero transfer. All absolute values and Money arithmetic use
their own precision contract, regardless of ambient Decimal context.

Example: V=100 USD, receive threshold=10, MTA=5, IA=0 gives T=90. With 10 settled
and 80 pending, Δ=0 while current positive risk remains 90. With no collateral,
V=15 gives Δ=5 and no transfer; V=16 gives a full 6 USD effective-value call.

IMPLEMENTATION DECISION: strict-greater MTA is this repository's declared policy,
not a universal interpretation of every CSA. The consolidated
[EU margin text, Article 25](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02016R2251-20230214)
provides context for suppressing amounts at/below MTA and transferring the full
amount above it. [BCBS margin requirements](https://www.bis.org/committees/bcbs/basel-framework/standard/mgn?allChapters=true)
distinguish initial and variation margin and discuss liquid collateral/haircuts.
Our nonzero thresholds, calendar timing and reusable IA are research policies;
they are not a claim to implement those regulatory requirements.

## Physical ledger, haircuts and FX

`src/parallax_risk/domain/portfolio/collateral.py` stores a frozen opening date,
one signed opening balance per currency and uniquely identified movements with
call/settlement dates and physical Money amounts. Append returns a new account.
Opening balances are effective at opening-day start; settlements on valuation
day count. Historical projections never include calls dated after that day.
Validate eligibility, agreed call frequency/settlement lag and every physical
balance state. One-way accounts cannot cross into the opposite holding direction;
returns are allowed up to the cash already held. Two-way ledgers may cross zero.

Effective cash value is sum(FX(balance_currency→agreement_currency) * balance *
(1-h)). Haircuts apply symmetrically to signed balances, not to the trade values.
This is cash-collateral valuation only; no security prices, funding costs, interest,
liquidation proceeds, segregation, custodians or haircut calibration are inferred.

Conversion requires an explicit direct quote with units QUOTE/BASE; no inverse or
cross quote is synthesized. A quote S settling at s converts today's values using
S(today)=S(s)*D_quote(s)/D_base(s), under the existing deterministic, frictionless
discounting assumptions. Required currency curves must cover s. Same-currency
conversion preserves Money. Binary64 FX factors become Decimal(str(factor)) for
exact-contract Money multiplication; this does not make market valuation exact
decimal. Precision loss beyond 34 significant arithmetic digits raises.

The call's transfer is an effective agreement-currency instruction, not physical
cash and not an executed payment. The caller chooses physical denominations and
records confirmed contractual movements explicitly. With h=.2, 125 nominal units
at same-currency FX=1 give 100 effective units. Automatically putting the 100-unit
instruction in the ledger would undercollateralize the account. No implicit inverse
haircut/FX division, allocation optimizer or settlement rounding is provided.

## Deterministic MPOR

`mpor_scenario` takes a caller-supplied set value and market at exactly default
date + CSA calendar MPOR. It freezes physical balances settled at default-day end,
ignoring later calls and settlements, including pre-default pending transfers.
Frozen foreign cash is revalued at closeout FX, retaining currency risk during the
freeze. R(closeout)=V(closeout)-C_frozen(closeout); positive risk=max(R,0).

ASSUMPTION: this is a deterministic scenario with explicitly chosen default and
closeout values. It does not draw defaults, derive a regulatory MPOR, model cure
periods, estimate IM, calculate closeout recoveries or simulate pathwise repricing.
See [ADR 0012](../decisions/0012-legal-portfolio-snapshots.md) and
[ADR 0013](../decisions/0013-collateral-ledger-and-margin-policy.md).

Phase 6 [pathwise exposure](EXPOSURE.md) composes this service and introduces a
restricted explicit simulator policy for perfect zero-haircut CSA-currency settlement.
It preserves these generic physical ledger conventions. Its grid EAD uses alive
collateral and does not attach this standalone frozen MPOR closeout implicitly.
