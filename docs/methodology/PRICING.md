# Deterministic pricing

## Intuition
Generate the contract's signed payments, find the relevant known/projected coupon
rates, and discount each future payment. Prices are conditional on the supplied
curves and conventions; they are not predictions of default or future exposure.

## Mathematics
For signed payment C_i at t_i, `PV_i=C_i*D_discount(t_i)` and `NPV=sum(PV_i)`.
Fixed coupon is `N*r*alpha`; floating coupon is `N*(g*L+s)*alpha`, where N is signed
notional, r fixed decimal annual rate, alpha accrual year fraction, g gearing, L
observed/projected index rate and s decimal annual spread. Pay-fixed swap PV is
floating minus fixed leg PV; receive-fixed reverses signs. No principal exchanges.

For direct spot S(s) QUOTE/BASE at settlement s and maturity T>=s:
`S(0)=S(s)*D_quote(s)/D_base(s)`, `F(T)=S(0)*D_base(T)/D_quote(T)`.
Buy-base forward receiving N BASE and paying N*K QUOTE has quote-currency value
`N*S(0)*D_base(T)-N*K*D_quote(T)`. K is the contractual quote/base strike. At K=F(T),
PV is zero under the documented frictionless/no-basis funding assumption.

## Implementation and assumptions
`src/parallax_risk/domain/pricing/engine.py` (`DiscountingEngine`, `forward_fx_rate`)
contains calculations; `results.py` stores signed contributions/model/input evidence.
Contracts in domain/instruments require supplied schedules/day counts/directions.
Known fixing on/before valuation is mandatory; future fixing uses an explicit index
curve. Same-day payments are excluded unless opted in, earlier payments always excluded.
Bonds are default-free dirty PV; no clean/ex-coupon/default/option adjustment exists.

Binary64 arithmetic is finite/range-checked; outputs wrap Decimal(str(value)) without
settlement rounding. This is different from exact Money primitive arithmetic.
Missing curves/fixings/FX, incompatible context, invalid schedules and arithmetic
range failures raise, rather than substitute a result.

## Tests and limits
`tests/quantitative/test_deterministic_pricing.py` checks independent 50-digit Decimal
formula targets, par instruments, two-day FX settlement and flow reconciliation.
Property/regression suites check signs, scale, paid flows and no hidden fallback.
Central sensitivity formulas/signs/bump errors are in [sensitivity](../validation/SENSITIVITY.md).
Full conventions, numerical tolerances and consulted sources are in
[deterministic methodology](deterministic-pricing.md). Separate Phase 3 analytical
rate options and [Heston calls](HESTON.md) support calibration; no pathwise repricing or XVA is present.
