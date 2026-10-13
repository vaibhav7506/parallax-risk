# CCR comparisons, illustrative capital and exceptions

`src/parallax_risk/domain/ccr/comparison.py` compares matching legal scope and
currency results. Challenger alpha must equal the explicit comparison policy.
Difference signs are challenger minus standardized. Standardized PFE is a formula
add-on; empirical quantile PFE and expected exposure are different objects.

The component bridge is +challenger EAD -alpha*RC -alpha*PFE
+(uncapped standardized EAD - capped standardized EAD). Its sum explains EAD
movement; a separate residual always reports binary64/Decimal conversion effects.
This is arithmetic driver attribution, without causal, Greek, sensitivity or
Shapley claims. Trade/group effective-notional and maturity-factor drivers remain
available in the standardized result. It does not reprice input counterfactuals.

Caller-supplied nonnegative risk weight w gives illustrative RWA=EAD*w. A ratio
k in [0,1] gives illustrative capital=RWA*k. Report both inputs and endpoint
differences, retaining policy hash/source. No ratings lookup, IRB rule, CVA capital
charge, leverage capital, jurisdictional minimum or regulatory weight is inferred.
These outputs are capital inputs for research comparisons, not required capital.

## Exception semantics

An exception requires abs(EAD difference)>absolute monetary tolerance AND
abs(relative difference)>relative tolerance. Equality does not trigger. Relative
difference uses standardized EAD as denominator. At zero reference, it is null;
the absolute threshold alone decides. No infinity or artificial denominator is
used. A flag is a caller-configured comparison exception, not a persisted Finding,
model-validation approval or breach of regulation. Negative inputs reject.

The synthetic demo defaults to 1 USD absolute/10% relative tolerances, weight 1,
ratio .08 and challenger alpha 1.4. These are labelled assumptions, not market
data or a universal regulatory recommendation. Tests check both strict threshold
boundaries, zero reference, capital differences and component reconciliation.

[Standardized methodology](STANDARDIZED_CCR.md), [IMM challenger](IMM_CHALLENGER.md),
[workflow](../workflows/CCR_WORKFLOW.md), [Phase 8 evidence](../validation/phase-8.md).
