# Deterministic portfolio workflow

1. Supply a frozen PortfolioSnapshot with explicit legal entities, scopes, existing
   contracts, signed positions, dates and CSA terms. Supply one uniquely identified
   CollateralAccount per CSA scope, including any known pending physical transfers.
2. Supply PricingContext and RunContext; portfolio and market dates must match.
   Same-day payment inclusion is rejected because the book uses end-of-day cutoff.
3. `src/parallax_risk/application/portfolio.py` injects PortfolioPricer and safe logger.
   DiscountingEngine implements the port. Only active booked contracts are priced;
   quantity multiplication preserves their signs. Inactive contracts contribute zero.
4. Verify every PricingResult's date, currency and instrument/market/curve fingerprints.
   Missing curves/fixings/FX and inconsistent pricer output propagate explicit errors.
5. Domain aggregation converts within each legal scope, calculates gross/net risk,
   values settled collateral and calculates pending-aware effective margin instructions.
6. Add separate set risk magnitudes in portfolio currency. Never offset collateral or
   risk across legal scopes or counterparties. Return prices, scope results, account
   hashes, book/market/curve hashes and RunContext; preserve the original inputs too.

Portfolio logs expose start/completed/failed, run ID, outcome and authored error type,
without book contents. No database write, HTTP risk endpoint, RNG, calibration transfer
or simulated exposure profile is performed. External settlement and physical allocation
remain explicit caller responsibilities. Call calculations do not append movements.

Run [the synthetic tutorial](../tutorials/04-FIRST-PORTFOLIO-RUN.md). Read the
[financial formulas and limits](../methodology/PORTFOLIO_COLLATERAL.md) before changing
signs, dates, FX or thresholds. Tests live in `tests/unit/test_portfolio_contracts.py`,
`tests/quantitative/test_collateral_netting.py` and
`tests/integration/test_portfolio_workflow.py`.
