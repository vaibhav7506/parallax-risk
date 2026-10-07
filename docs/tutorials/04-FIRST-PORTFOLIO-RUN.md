# First synthetic portfolio run

Use the installed project virtual environment from repository root:

```powershell
.venv\Scripts\python.exe scripts/demo_portfolio.py
```

`scripts/demo_portfolio.py` validates the existing explicitly synthetic
`data/sample/phase2_market.json`, constructs declared curves and creates a versioned
book with one entity, one enforceable USD set and +100/-80 USD future cash flows.
The CSA has receive/post thresholds 10/20 USD, MTA 5 USD, zero IA, eligible USD/EUR
cash with 0/.2 haircuts, daily calendar calls, two-day settlement and ten-day MPOR.
The ledger has 5 USD settled and 4 USD pending. The production PortfolioService
prices, nets and calculates settled residual risk and a pending-aware instruction.

Stdout is JSON containing synthetic-data label, full portfolio/ledger and result
with stable hashes and fixed run metadata. Stderr contains safe workflow logs with
execution timestamps. Re-running in the same pinned environment reproduces stdout;
stderr timestamps naturally differ. No margin movement or database row is executed.
Do not treat future payments as today's exact NPV: the supplied curves discount them.

For multiple legal scopes/currencies, construct Counterparty/NettingSet tuples and
provide all required direct FX quotes/curves. For a timeline, append caller-confirmed
CollateralMovement values to a new account and evaluate at matching market dates.
For an MPOR scenario, supply closeout value/market at the exact declared endpoint;
the domain freezes settled physical balances at default. This tutorial does not
calculate stochastic exposure or CVA.

See [workflow](../workflows/PORTFOLIO_WORKFLOW.md),
[methodology](../methodology/PORTFOLIO_COLLATERAL.md),
[code guide](../CODEBASE_GUIDE.md) and [phase evidence](../validation/phase-5.md).
