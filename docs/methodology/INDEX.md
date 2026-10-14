# Implemented quantitative methodology

Start with intuition and units, then follow the source/test mapping. Mathematical
definitions are backed by actual implementation and tests.

- [Primitives: Money, dates, calendar/day-count/compounding](primitives.md).
- [Market data: observations, provenance and immutable content identity](MARKET_DATA.md).
- [Curves: discounting, projection, interpolation and bootstrap](CURVES.md).
- [Pricing: cash flows, bonds, swaps, FX and signs](PRICING.md).
- [Complete deterministic formulas, settings, limitations and consulted references](deterministic-pricing.md).
- [Sensitivity validation](../validation/SENSITIVITY.md).
- [Stochastic process and discretization contracts](STOCHASTIC_PROCESSES.md).
- [Vasicek](VASICEK.md), [Hull–White](HULL_WHITE.md), [GBM](GBM.md), [Heston](HESTON.md).
- [Correlation validation and explicit repair](CORRELATION.md).
- [Calibration, convergence and parameter uncertainty](CALIBRATION.md).

- [Monte Carlo paths and sequences](MONTE_CARLO.md).
- [Monte Carlo statistics and variance reduction](MONTE_CARLO_STATISTICS.md).

Phase 8 implements restricted comparative CCR prototypes. Phase 9 adds model-validation lab workflows; see [roadmap](../../ROADMAP.md).

- [Portfolios, legal netting and cash collateral](PORTFOLIO_COLLATERAL.md).

- [Conditional market paths, exposure statistics and grid EAD](EXPOSURE.md).
- [Hazard/survival/default and recovery assumptions](CREDIT_DEFAULT.md).
- [Wrong-way risk scenario policies](WRONG_WAY_RISK.md).

- [Unilateral CVA/DVA and signed XVA](XVA.md).
- [Additive funding and external segregated IM](FUNDING_MARGIN.md).
- [Actual XVA sensitivities and ordered residual attribution](XVA_SENSITIVITIES.md).

## Phase 8

- [Restricted SA-CCR-inspired formulas and supported contracts](STANDARDIZED_CCR.md)
- [Actual legal-unit IMM challenger and effective EE/EPE](IMM_CHALLENGER.md)
- [Illustrative capital, arithmetic drivers and exception policy](CCR_COMPARISON.md)

These research methods do not establish regulatory compliance or model approval.

## Phase 9

- [Comparable models and numerical checks](MODEL_VALIDATION.md)
- [Independent bootstrap and calibration/parameter uncertainty](MODEL_UNCERTAINTY.md)
- [Sourced and hypothetical stresses](STRESS_SCENARIOS.md)
