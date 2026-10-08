# Your first exposure and credit run

From the repository root with the locked environment installed:

```sh
python scripts/demo_exposure.py
```

`src/parallax_risk/application/exposure_examples.py` constructs 256 labelled synthetic
paths for a long EUR/USD FX forward, equal deterministic 3% currency rates and zero
Q FX drift. The FX volatility is 50% annually, spread volatility 80%, FX/spread Brownian
correlation .7, recovery .4 and baseline annual intensity .2. Civil dates in 2025 use
ACT/365F. All are explicit example assumptions, not observed market data or forecasts.

The script prints full inputs and independent, static-rank rho=.7 and dynamic-spread
results. Compare EE/ENE/EPE, 95%/99% PFE, survival, default counts and grid EAD.
The market digest is common across cases. Static ranking preserves the sampled default
marginal; dynamic spreads need not preserve it. An EAD comparison ratio is neither CVA
nor a standalone measure of dependence when the marginal changes.

Run the command twice in the pinned environment and compare stdout bytes. Fixed
run IDs/time and owned sequence addresses support replay. Runtime metadata can differ
across environments; no universal bitwise compatibility is promised. Customize
`example_inputs`, or inject your own valid request/book/market provider into
ExposureService. Reject inconsistent dates, currencies, fixings and CSA policies;
there is no silent repair.

For daily cash calls, supply daily calendar dates and zero-haircut CSA-currency cash.
The published right-grid default exposure uses alive-path collateral and omits a
default-conditioned margin freeze/MPOR. Read those limits before interpreting results.
[Workflow](../workflows/EXPOSURE_WORKFLOW.md), [definitions](../methodology/EXPOSURE.md),
[credit](../methodology/CREDIT_DEFAULT.md), [WWR](../methodology/WRONG_WAY_RISK.md),
[actual verification](../validation/phase-6.md). XVA is Phase 7, NOT IMPLEMENTED.
