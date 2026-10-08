# Exposure and credit workflow

1. Construct an immutable nonempty-counterparty PortfolioSnapshot with supplied
   legal attestation, signed positions, origin date and reporting currency.
2. Construct SimulationRequest with explicit Q model components, units, addressed
   sequence, correlation, path/batch counts and ACT/365F date grid.
3. Bind ConditionalMarketScenario rate currencies, projection indices, direct FX,
   horizon-covering curve knots and known origin fixings. Future fixing dates inside
   the horizon must be on the grid.
4. Supply one initial CollateralAccount per CSA scope, with no pending/future origin
   calls. Automated settlement uses zero-haircut CSA-currency cash and daily calendar
   grids. Empty uncollateralized scopes remain valid.
5. Optionally supply unique CreditScenario per counterparty with aligned hazard horizon,
   recovery, separate threshold addresses and explicit independent/static/dynamic policy.
   Static ranking needs another unique address; dynamic spread needs a bound Q GBM.
6. Inject engine, PortfolioService, logger and fixed RunContext into ExposureService.
   It consumes contiguous batches, reprices each path/date, advances path-specific
   ledgers/fixings and rejects missing, extra or incorrectly dated market contexts.
7. Inspect immutable positive/negative path buffers, per-counterparty and total profiles,
   market-path digest, book/account/scenario/credit hashes and runtime/sequence metadata.
   Baseline/scenario survival and grid EAD explain the comparison's scope.

`src/parallax_risk/application/exposure.py` composes the existing simulation and
portfolio services. `src/parallax_risk/domain/exposure/` and `domain/credit/` own math.
No API handler, persistence, environment-loaded setting or global RNG is required.
The default 256 MiB output cap checks the two retained exposure matrices only; it is
not a peak-memory limit. Quantile copies, survival/default arrays and simulation
working buffers add memory. This is a serial CPU research collector, not distributed
or production financial job infrastructure. No inference interval is reported.

Use [the tutorial](../tutorials/05-FIRST-EXPOSURE-RUN.md) and preserve full input JSON,
source/environment evidence and method assumptions. See [exposure](../methodology/EXPOSURE.md),
[credit](../methodology/CREDIT_DEFAULT.md), [WWR](../methodology/WRONG_WAY_RISK.md),
[replay](../REPRODUCIBILITY.md) and [limits](../LIMITATIONS.md).
