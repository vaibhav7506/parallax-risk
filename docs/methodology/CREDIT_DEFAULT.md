# Finite-horizon hazard, survival and default sampling

Phase 6 credit curves are supplied model assumptions, not calibrated CDS curves.
`src/parallax_risk/domain/credit/hazard.py` owns PiecewiseHazardCurve and
RecoveryAssumption; `src/parallax_risk/domain/credit/dependence.py` owns sampling
and the stochastic-spread protocol. No credit instrument or default-loss valuation
is added.

## Definitions and conventions

Times are years from a surviving origin, begin at zero and strictly increase.
Each nonnegative annual intensity h_i applies on [t_i,t_(i+1)); cumulative hazard
H(t) integrates supplied intervals. S(t)=exp(-H(t)), F(t)=-expm1(-H(t)), and
interval default mass is S(a)*(1-exp(-(H(b)-H(a)))). expm1 preserves small PDs.
No extrapolation, negative hazards or nonfinite arithmetic is accepted. Legitimate
binary64 exponential underflow gives survival zero; integrated-hazard overflow
and default-time resolution failure are explicit errors, not repaired inputs.

Draw positive unit exponential E from an owned addressed PCG64DXSM generator.
Solve H(tau)=E piecewise, including a default exactly at the final endpoint.
Zero-hazard intervals contribute no default mass. No default within the finite
horizon is None, never infinity or an artificial tail extrapolation. Recovery is a
constant fraction in [0,1]; LGD is its complement. Phase 6 does not multiply exposure
by LGD or discount it into a loss.

## Stochastic credit spreads

StochasticCreditSpread is an injectable runtime protocol with recovery, a declared
SHA-256 policy hash and intensity(spread). ReducedFormSpread implements
lambda=s/(1-R), requires R<1 and a finite nonnegative annual decimal spread.
This credit-triangle approximation is a research assumption, not a calibrated
CDS pricing relation. Dynamic scenarios bind a Q GBM annual-spread component.
Use left endpoint intensities on each market grid interval and invert the resulting
pathwise integrated hazard with separate independent exponential thresholds.
Terminal spread does not determine the preceding interval's hazard.

Conditional survival is exp(-integral lambda_i); the result reports its sample mean
at each grid date separately from deterministic baseline survival. Adding stochastic
spreads generally changes the marginal survival curve. There is no hidden shift or
calibration to preserve the baseline. Constant spread reproduces the deterministic
curve when the supplied intensity agrees. See [dependence](WRONG_WAY_RISK.md).

## Quantitative checks

Piecewise integrals, endpoint inversion, zero hazard, tiny default probabilities,
underflow, recovery boundaries and rejected overflow/resolution are tested directly.
A 50,000-threshold deterministic experiment checks the analytical CDF at several
points within six binomial standard errors. A 20,000-path stochastic intensity
experiment compares sampled default probability with mean conditional survival
using six binomial standard errors. These tests validate supplied mathematics,
not market calibration or regulatory approval.

[Exposure/EAD](EXPOSURE.md), [tests](../testing/STRATEGY.md),
[Phase 6 evidence](../validation/phase-6.md).
