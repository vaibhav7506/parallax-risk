# Unilateral credit adjustments and signed XVA

Phase 7 adds a valuation-adjustment layer to actual Phase 6 exposure. It reports
four signed components in one reporting currency, with interval contributions,
input fingerprints, assumptions and run evidence. This is an additive research
approximation. It does not solve a bilateral first-to-default or recursive price.

## Credit formulation and units

Let EE(t) be expected positive residual exposure and ENE(t) the nonnegative
magnitude of negative residual exposure after eligible settled collateral and
within-set legal netting. Neither is a signed NPV. D(t) is a supplied deterministic
reporting-currency discount factor anchored at the exposure origin. Time is
ACT/365F years, hazards are annual decimal intensities, and recovery R is a
constant fraction in [0,1]. LGD = 1-R. Curves must cover the finite exposure horizon;
XVA rejects extrapolation even if a curve's own policy would permit it.

Under independent deterministic credit, with survival S(t):

```text
CVA adjustment = -LGD_c * integral D(t) EE(t) d(1-S_c(t))
DVA adjustment = +LGD_b * integral D(t) ENE(t) d(1-S_b(t))
```

The own curve is independent of market and counterparty. DVA is a unilateral
own-default benefit. It includes no counterparty-survival/first-to-default filter.
Adding these components is a declared approximation, not bilateral closeout.
Independent factorization also excludes stochastic discount/exposure covariance.

## Implemented numerical rule

`credit_integral` refines the grid on the union of exposure, discount and hazard
knots within the profile horizon. Exposure is linearly interpolated between
supplied endpoints. The hazard curve supplies exact default mass on each interval:

```text
deltaPD_i = S(a) * -expm1(-(H(b)-H(a)))
loss_i = LGD * [D(a)EE(a) + D(b)EE(b)]/2 * deltaPD_i
```

This endpoint-average approximation does not exactly integrate a varying discounted
profile. With constant exposure and zero discount rate it gives the exact known
target LGD*EE*(1-exp(-lambda*T)). Grid refinement is an accuracy control; it is
separate from Monte Carlo path count. No monotonicity in exposure over time is assumed.

For STATIC_RANK and DYNAMIC_SPREAD scenarios, XvaService instead uses actual sampled
defaults and their path exposures:

```text
CVA adjustment = -mean_paths[1(tau<=T) * D(bucket(tau)) * LGD * EAD_path]
```

Nondefaults contribute zero. The sampled indicator already supplies default
probability: **do not multiply by PD again**. Contributions are grouped by the first
grid endpoint >= tau. They inherit Phase 6 alive-path collateral, without
default-conditioned freeze/MPOR or interpolation to tau. This can bias loss near
maturity. Static rank is a non-adapted stress. Dynamic hazard is left-grid and its
marginal survival need not equal baseline survival. Comparing its CVA with the
independent quadrature changes both marginal/estimator assumptions; it is not by
itself an isolated measure of dependence.

## Result contract and validation

`XvaResult` requires CVA, DVA, FVA, MVA exactly once in that order. CVA/MVA
contributions are <=0, DVA >=0, and FVA may have either sign. Each component's
binary64 contributions reconcile to its unrounded Decimal Money representation;
FVA reconciles to -FCA+FBA within 1e-12 times max(1, absolute expected FVA).
Total adjustment is the checked sum of the four components, not a supplied clean
price. Decimal Money preserves currency arithmetic; numerical integration and
simulation remain binary64 valuation.

Per-name contribution labels identify actual ACT/365F intervals. Aggregate labels
identify counterparties; they are not time buckets. Aggregate adjustments add
separate legal-entity results without new cross-name netting. XvaService verifies
credit identity, origin date, run metadata and calculator input evidence. Hashes
identify contents; they are not institutional approvals or persisted lineage.

Independent zero-hazard, full-recovery and zero-exposure limits are checked.
Generated constant-exposure cases test only justified hazard/recovery monotonicity.
Varying discount quadrature has a known analytical target and refinement check.
Sampled examples test zero defaults and the absence of a second PD multiplier.
See [Phase 7 evidence](../validation/phase-7.md).

## Code and references

`src/parallax_risk/domain/xva/calculators.py`,
`src/parallax_risk/domain/xva/contracts.py`, `src/parallax_risk/application/xva.py`,
`tests/quantitative/test_xva.py`, `tests/unit/test_xva_contracts.py`.

[Funding and margin](FUNDING_MARGIN.md), [risk](XVA_SENSITIVITIES.md),
[workflow](../workflows/XVA_WORKFLOW.md), [ADR 0017](../decisions/0017-unilateral-credit-adjustments.md).
The [Federal Reserve CVA research discussion](https://www.federalreserve.gov/pubs/feds/2010/201010/index.html)
is background on expected default loss, not a claim of implementing supervisory rules.
