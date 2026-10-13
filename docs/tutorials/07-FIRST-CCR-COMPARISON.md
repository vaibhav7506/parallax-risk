# Your first CCR comparison

Install the current release as described in [local setup](../operations/LOCAL_SETUP.md).
Run from the repository root:

```sh
python scripts/demo_ccr.py
```

`src/parallax_risk/application/ccr_examples.py` composes actual production
simulation, portfolio pricing, exposure and comparison services. The example is
explicitly synthetic: 100 EUR BUY_BASE FX forward, USD quote leg, strike/spot 1.1,
equal deterministic .03 currency rates, Q FX volatility .5, seed 20261001 and
256 paths. The quarterly ACT/365F grid includes origin and final one-year maturity.
The inherited unused spread component does not affect this CCR calculation; no
credit/default model is substituted for exposure. Fixed run/source metadata
supports repeatable output; it is not a fabricated repository commit.

Inspect `research.scopes[0].comparison`: standardized RC/add-on/multiplier/PFE,
uncapped/capped EAD, challenger EE/effective EE/EPE, illustrative RWA/capital,
signed differences, exception and bridge residual. Inspect the enclosing input
and positive-path hashes. JSON contains `is_sample=true` and
`regulatory_compliance=false`. Quantitative calculation is binary64, with
unrounded Money output; extra decimal digits do not establish model accuracy.

Origin clean value is theoretically zero for this at-the-money forward. Binary64
pricing retains a tiny residual (about 1.4e-14 USD in the verified Windows sample),
without clamping. The standardized
foreign-leg notional is approximately 110 USD, add-on approximately 4.4 USD and
EAD approximately 6.16 USD. Challenger EAD depends on the actual finite path
sample and supplied time grid. Increasing path count requires an accuracy/convergence
study; no approval or regulatory compliance follows from a numerical match.

[Workflow](../workflows/CCR_WORKFLOW.md), [methodology](../methodology/STANDARDIZED_CCR.md),
[assumptions](../methodology/IMM_CHALLENGER.md),
[comparison terms](../methodology/CCR_COMPARISON.md), [limitations](../LIMITATIONS.md),
[actual verification](../validation/phase-8.md).
