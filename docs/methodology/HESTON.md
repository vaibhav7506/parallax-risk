# Heston stochastic volatility and European calls

## Intuition

Asset variance moves towards a long-run level instead of remaining constant.
Correlation between price and variance shocks produces skew. Negative correlation
often makes falls in price coincide with rises in variance. This is a model assumption,
not a claim about any actual observed asset.

## Mathematics and units

Under Q, `dS=(r-q)S dt+sqrt(v)S dW_s` and
`dv=k(theta-v)dt+xi sqrt(v)dW_v`, with `dW_s dW_v=rho dt`.
S>0, v>=0, k>0, theta>=0, xi>=0 and rho in [-1,1]. Rates r/q are continuous annual
decimals. Variance v/theta is squared annualized relative volatility; xi is volatility
of variance in the corresponding time convention. The model records the Feller
margin `2k theta-xi²`; a negative margin is allowed and exposes an attainable zero
boundary. It is not silently projected into a Feller-constrained parameter space.
For independent shocks z1,z2, variance uses `rho*z1+sqrt(1-rho²)*z2`.

## Discretization

Heston in `src/parallax_risk/domain/models/assets.py` supplies coefficients.
HestonProjectedEuler in `src/parallax_risk/domain/models/discretization.py` uses
`S_next=S exp[(r-q-v/2)h+sqrt(v h)z1]` and
`v_proposal=v+k(theta-v)h+xi sqrt(v h)z_v`, then `v_next=max(0,v_proposal)`.
`step_with_diagnostics()` reports the proposal and whether projection occurred.
This is **projected Euler**, not full-truncation Euler or an exact Heston transition.
Projection introduces bias. Generic Euler regularity/order results do not apply at
the square-root boundary. ExactTransition raises ModelError for Heston.

## European pricing

`src/parallax_risk/domain/models/heston_pricing.py` evaluates the log-spot characteristic
function using the stable decaying-exponential Riccati form associated with
[Albrecher et al., The Little Heston Trap](https://www.ma.imperial.ac.uk/~ajacquie/IC_Num_Methods/IC_Num_Methods_Docs/Literature/HestonTrap.pdf).
Define iu=i*u, beta=k-rho*xi*iu, `d=sqrt(beta²+xi²(u²+iu))` with principal root,
`h=(u²+iu)/(beta+d)`, `g=-xi²*h/(beta+d)` and E=exp(-dT).
Then `D=-h(1-E)/(1-gE)`, `C=k theta[-hT-2log((1-gE)/(1-g))/xi²]`,
and `phi(u)=exp(iu[log(S)+(r-q)T]+C+Dv0)`.

Rationalizing beta-d prevents loss of precision as xi becomes small. Complex log1p
and expm1 use 8-term Taylor expansions for argument magnitude below 1e-4; omitted
terms are O(magnitude^9). xi=0 is the exact deterministic-variance Gaussian limit,
not a threshold-based fallback. Absorbing v0=theta=0 is also evaluated analytically.

Lewis inversion calculates a one-unit European call:
`call=S exp(-qT)-exp(-rT)sqrt(K)/pi * integral_0^infinity
 Re[exp(-iu log K)phi(u-i/2)]/(u²+1/4) du`.
SciPy QUADPACK integrates the infinite domain. Default price-error gate is 1e-7
currency units, relative integration tolerance 1e-9, subdivision limit 250.
HestonCallPrice records value, price-scaled estimated error, evaluations, method
and Feller margin. Non-convergence, excessive estimated error, nonfinite results or
no-arbitrage violations raise NumericalError; prices are never clipped.

## Calibration, validation and limitations

HestonCallProblem fits k,theta,xi,rho,v0 against explicitly sourced call premiums,
with fixed spot/r/q. The synthetic example has twelve calls across four maturities
and three strikes, generating parameters (1.5,.045,.35,-.65,.035).
See [calibration methodology](CALIBRATION.md) and `python scripts/demo_calibration.py`.

`tests/quantitative/test_stochastic_models.py` independently integrates the Riccati
ODE, checks the Gaussian price limit, small xi down to 1e-10, numerical-tolerance
stability and correlation endpoints. 10.39421856515 is a recorded numerical
regression case, not an independently certified vendor price.
`tests/quantitative/test_calibration.py` checks actual five-parameter recovery/replay.

Only European calls, constant parameters, continuous deterministic rates/dividends
and unit underlying premiums are supported. No implied-volatility solver, puts,
surface smoothing, American exercise, jumps or Heston exact simulation exists.
Quadrature errors are estimates, not rigorous error bounds, and exclude parameter
or model uncertainty. General complex-moment-domain certification is absent; pricing
uses Im(u)=-1/2. Very extreme/underflowing coefficients can fail explicitly. A fit
can have multiple minima or weak parameter identification; synthetic recovery does
not establish real-market performance.
