# Implemented model cards

These cards describe release 0.12.0 research models. Their implementation versions
remain the versions of the underlying engines; the service release does not change
their mathematics. All demonstration observations are synthetic. Model inventory,
review frequency and approval authority are explicit governance inputs, not inferred
from these cards. No model is certified for trading or regulatory submission.

| Model / purpose | Implemented inputs and units | Validation evidence | Material limitations |
|---|---|---|---|
| Vasicek — Gaussian Q short rates and discount-factor calibration | Positive mean reversion in 1/year, long-run decimal annual rate, nonnegative rate volatility per square-root year; fixed initial rate | Independent integrated Gaussian moments, small-mean-reversion stability, synthetic calibration recovery/repeatability | Constant coefficients, negative rates permitted, weak curve-only identification; exact marginal transition excludes a joint stochastic rate integral |
| Hull–White one factor — initial-curve fit and bond-option calibration | Gaussian factor with positive mean reversion; nonnegative volatility; explicitly smooth initial forward curve; European bond-option prices | Initial curve fit, exact factor moments, independent Gaussian option integration and actual bounded calibration | Restricted smooth initial curve, Gaussian rates, European bond options; no swaption pricer or exact joint rate/discount simulation |
| GBM — positive asset paths and known-moment Monte Carlo checks | Finite annual drift, nonnegative relative volatility per square-root year, strictly positive spot, explicit year-fraction grid | Analytical transition, known terminal moments, path convergence, positivity properties | Constant coefficients; no smile, jumps, historical estimation or GBM calibration objective; Euler can fail on negative proposed spot |
| Heston — stochastic variance and European-call calibration | Positive spot, nonnegative variance/long-run variance, positive mean reversion, nonnegative volatility of variance, correlation in [-1,1]; continuous rates/dividends | Independent Riccati ODE, Gaussian limit, small volatility-of-variance stability, actual five-parameter synthetic fit | Projected Euler has boundary bias; no exact transition; only European call pricing; quadrature error estimates are not rigorous bounds; multiple fit minima possible |
| Reduced-form credit and wrong-way scenarios — survival/default and exposure coupling | Nonnegative piecewise hazards in 1/year, recovery in [0,1], explicit spread/recovery mapping, addressable credit sequence and declared dependence policy | Independent survival/default probabilities, inverse sampling, independence and correlation scenario checks | Declared hazard/recovery/WWR assumptions; grid default/EAD; spread mapping does not infer a CDS convention or empirical dependence |
| Exposure and additive XVA — legal-unit profiles and signed adjustments | Explicit legal netting, CSA currency/threshold/MTA/haircut/lag, daily collateral grid, market bindings; currency-valued EE/PFE; CVA/DVA and FVA/MVA inputs | Independent collateral/netting cases, analytic credit checks, actual exposure/XVA replay, finite-difference checks and ordered residual evidence | Unilateral credit approximations; discrete MPOR; supplied funding/external segregated IM; no joint-first-default or recursive funding solution; small demo path counts do not validate tails |
| Restricted standardized CCR and IMM challenger — comparative EAD/capital inputs | Supported FX/rate contract mapping, declared supervisory factors, business-day MPOR/NICA, effective EE/EPE and illustrative capital ratio/weights | Hand-calculated supported-contract cases, actual legal-unit repricing and comparison/driver residual checks | SA-CCR-inspired restricted prototype and internal-model challenger; no full regulatory asset classes, official calibration, approval or compliance claim |

## Source, conventions and tolerances

Process implementations: `src/parallax_risk/domain/models/rates.py`,
`src/parallax_risk/domain/models/assets.py`,
`src/parallax_risk/domain/models/discretization.py` and
`src/parallax_risk/domain/models/heston_pricing.py`.
Calibration: `src/parallax_risk/domain/calibration/problems.py`.
Credit/exposure/XVA/capital: `src/parallax_risk/domain/credit/`,
`src/parallax_risk/domain/exposure/`, `src/parallax_risk/domain/xva/` and
`src/parallax_risk/domain/ccr/`.

[Vasicek](../methodology/VASICEK.md), [Hull–White](../methodology/HULL_WHITE.md),
[GBM](../methodology/GBM.md), [Heston](../methodology/HESTON.md),
[calibration](../methodology/CALIBRATION.md),
[credit](../methodology/CREDIT_DEFAULT.md), [WWR](../methodology/WRONG_WAY_RISK.md),
[exposure](../methodology/EXPOSURE.md), [XVA](../methodology/XVA.md),
[funding/IM](../methodology/FUNDING_MARGIN.md) and
[CCR](../methodology/CCR_COMPARISON.md) retain formulas, signs, conventions,
acceptance tolerances and detailed assumptions. Pricing uses finite binary64;
Money ledger addition is exact Decimal within its separate contract.

Quantitative checks live in `tests/quantitative/test_stochastic_models.py`,
`tests/quantitative/test_calibration.py`, `tests/quantitative/test_simulation_paths.py`,
`tests/quantitative/test_simulation_convergence.py`,
`tests/quantitative/test_credit_exposure.py`, `tests/quantitative/test_collateral_netting.py`,
`tests/quantitative/test_xva.py` and `tests/quantitative/test_ccr.py`.
Actual environment/results are in the [phase reports](../validation/OVERVIEW.md).
The [service demonstration](../api/EXAMPLES.md) uses these engines, and its successful
jobs retain input, result and lineage. [Limitations](../LIMITATIONS.md) remain applicable
when a model is exposed through HTTP or CLI.
