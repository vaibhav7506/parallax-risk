# Sensitivity definitions and checks

## Intuition
Reprice with small up/down input changes to estimate local response. The bump's units,
which curves change and which observed fixings stay fixed define the risk measure.

## Mathematics
For positive declared h, `dPV/dr≈(PV(+h)-PV(-h))/(2*h)` per unit decimal annual rate.
`PV01=dPV/dr*0.0001`; this project's `DV01=-PV01`, not absolute value. A continuous-zero
knot shift b changes node discount D_i to `D_i*exp(-b*t_i)` where t_i is curve time.
With log-linear D this is parallel between knots; linear-D risk is a knot shift.
It is not calibrated market-quote DV01.

FX delta is `(PV(S+h)-PV(S-h))/(2*h)` per one QUOTE/BASE direct-spot unit, with curves
fixed. Settlement-date spot conversion is included, so unit analysis is essential.

## Code, validation and limits
`src/parallax_risk/domain/pricing/sensitivities.py` implements
`parallel_rate_sensitivity` and `fx_delta`; results preserve base/up/down evidence.
Explicit IDs select unique known curves; all assignments of shared IDs change
consistently. Historical fixings stay fixed. Invalid/nonpositive FX shocks, bumps
below binary64 resolution and nonfinite/range arithmetic raise explicit errors.

Quantitative tests compare a zero-coupon bond rate derivative to `-T*N*exp(-r*T)` and
FX delta to its linear spot formula including settlement. Relative tolerances are
1e-9 with h=1e-5, 1e-8 with h=1e-4 for the rate case (central truncation bias), and
1e-10 for the FX derivative. Property checks cover direction reversal; rejection
tests cover invalid/unresolvable bumps. No Monte Carlo gradient or attribution model exists.
