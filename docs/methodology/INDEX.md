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

Stochastic exposure/default credit, wrong-way
risk, XVA, capital and risk attribution are NOT IMPLEMENTED. Their detailed model
documents will be created with actual authorized implementations; see [roadmap](../../ROADMAP.md).

- [Portfolios, legal netting and cash collateral](PORTFOLIO_COLLATERAL.md).
