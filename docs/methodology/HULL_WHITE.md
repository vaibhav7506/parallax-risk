# Hull–White one-factor short rates

## Intuition

Hull–White adds a time-dependent shift to a mean-reverting Gaussian factor so that
initial default-free discounts match a specified curve. Matching that curve alone
does not identify mean reversion or volatility; option observations are needed.

## Mathematics and assumptions

Under Q, `r(t)=x(t)+phi(t)`, `dx=-a x dt+sigma dW`. Here a>0, sigma>=0 and
`phi(t)=f(0,t)+sigma² B(a,t)²/2`, where `B(a,t)=(1-exp(-a t))/a`.
Our explicitly smooth initial curve has `f(0,t)=level+slope*t` and
`P(0,t)=exp(-level*t-slope*t²/2)`. Level is a decimal annual rate and slope is
rate/year. Negative forwards are valid. Initial rate must equal f(0,0) to reproduce
this initial curve. Arbitrary conditioned future rates are valid.

The drift is `a[f(0,t)-r]+slope+sigma² B(2a,t)`; diffusion is sigma.
Conditional mean is `(r-phi(t))exp(-a h)+phi(t+h)` and variance is
`sigma² B(2a,h)`. Bonds with T>=t use
`P(t,T)=P(0,T)/P(0,t)*exp(B(a,T-t)[f(0,t)-r]-sigma² B(2a,t)B(a,T-t)²/2)`.

A time-0 European call on a unit bond maturing at T, expiring at e<=T, with
strike K paid at expiry, has price `P(0,T)N(d1)-K P(0,e)N(d2)`. Its standard
deviation is `s=sigma B(a,T-e)sqrt(B(2a,e))`,
`d1=log(P(0,T)/(K P(0,e)))/s+s/2`, `d2=d1-s`.
For s=0 the deterministic intrinsic value is used exactly.

## Implementation

HullWhite and LinearForwardCurve are in `src/parallax_risk/domain/models/rates.py`.
The smooth curve is explicit; no finite-difference derivative of a piecewise
Phase 2 interpolated curve is guessed. expm1-based OU loadings stabilize small a*t.
This shifted representation agrees with the
[QuantLib process formulation](https://github.com/lballabio/QuantLib/blob/master/ql/processes/hullwhiteprocess.cpp).
All options are European, default free and single currency; rates/volatility are constant.

## Calibration, tests and limitations

HullWhiteBondOptionProblem in `src/parallax_risk/domain/calibration/problems.py`
fits a and sigma to six synthetic bond calls across expiry/maturity pairs. Truth
(.18, .012) uses initial forward level .03 and slope .001.
`python scripts/demo_calibration.py` computes the fit and its evidence.

`tests/quantitative/test_stochastic_models.py` checks time-0 curve fitting, shift
derivative/drift, conditional Gaussian-integral bonds and independent bond-option
payoff integration. `tests/quantitative/test_calibration.py` checks recovery.
Only the linear instantaneous forward representation is supported. Piecewise market
curve smoothing, cap/swaption calibration, time-dependent coefficients and joint
rate/discount-factor simulation are NOT IMPLEMENTED. The one-factor Gaussian
model permits negative rates and cannot reproduce arbitrary rate smiles.
