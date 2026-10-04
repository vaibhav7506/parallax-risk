# Curves and bootstrap

## Intuition
A discount curve tells how much a future payment is worth now. A projection curve
implies an index rate for an accrual interval. They may differ and are assigned explicitly.

## Mathematics and units
Let D(t)>0 be the discount to declared time t, with D(0)=1; alpha is the contractual
day-count fraction from a to b. Continuous zero rate is `z(t)=-log(D(t))/t`, t>0.
Simple projected forward is `L(a,b)=(D_projection(a)/D_projection(b)-1)/alpha`.
Negative rates can imply D(t)>1; positivity is required, decreasing discounts are not.

For node weight w, linear ordinates are `(1-w)*y_left+w*y_right`; log-linear discounts
are `exp((1-w)*log(D_left)+w*log(D_right))`. Discount extrapolation either errors or
holds the terminal continuous zero rate; ZeroCurve holds its declared quoted zero
rate under its compounding policy. Sampling ZeroCurve into DiscountCurve preserves
knots but may change between-knot values.

Deposit bootstrap rate is `(1/D(T)-1)/alpha`; single-curve par swap rate is
`(1-D(T))/sum(alpha_i*D(T_i))`. T is final payment and alpha_i the supplied fixed-leg
accrual. The par formula assumes valuation-date start, no lag, constant notional and
zero floating spread. This is not a dual-curve/basis calibration formula.

## Implementation, failure and validation
`src/parallax_risk/domain/market/curves/term_structures.py` defines DiscountCurve,
ZeroCurve, ForwardCurve and CurveSet. `interpolation.py` holds the typed strategies;
`bootstrap.py` holds supported quotes and bounded bisection; `diagnostics.py` reports
positive-DF/monotonicity diagnostics without rejecting legitimate negative rates.

The default positive DF bracket is [1e-8,10], annual quote residual gate 1e-12,
DF tolerance max(1e-13,1e-12*scale), and iteration cap 200. Bounds are numerical,
not economic plausibility limits. Failed bracket/convergence/final repricing returns
no partial curve. Out-of-horizon requests fail unless extrapolation was explicit.

`tests/unit/test_curves_bootstrap.py` and property/quantitative tests cover hand-derived
nodes, interpolation, negative rates, short accruals, failure gates and par instruments.
See [complete policy/references](deterministic-pricing.md) and
[ADR 0007](../decisions/0007-deterministic-curves-and-pricing.md).
