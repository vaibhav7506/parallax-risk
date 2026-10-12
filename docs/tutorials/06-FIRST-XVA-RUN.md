# Your first XVA research run

Use the locked project environment from [local setup](../operations/LOCAL_SETUP.md).
From the repository root, run:

```sh
python scripts/demo_xva.py
```

The demo uses a synthetic EUR/USD forward, deterministic equal currency rates,
64 addressed market paths, supplied credit/recovery and funding spreads, and an
external constant posted IM profile. They are research assumptions, not observed
quotes or calibrated bank inputs. Full inputs and fixed run metadata appear in JSON.

Inspect `research.valuations`: three actual runs use independent, static rank and
dynamic spread credit. Each has separate counterparty components, signed aggregate
CVA/DVA/FVA/MVA, FCA/FBA, assumptions and exposure/input hashes. Top-level
`total_adjustments` adds the four signed components; it is not a clean-plus-adjusted
replication price. Different credit estimators/marginals preclude attributing the
whole difference to dependence alone.

Inspect `research.fx_sensitivity`: base, +/-0.001 and +/-0.0005 spot valuations
produce per-unit derivatives for all four components and TOTAL. Reported stability
differences are observations, not guarantees. `research.attribution` reprices ordered
spot +0.02 and annual credit-triangle spread +0.002; inspect component movements and
the explicit actual-minus-ladder residual.

For a custom library call, start with the production `experiment()` factory, replace
validated immutable inputs, and explicitly compose XvaRevaluation with ExposureService
and XvaService. The [workflow](../workflows/XVA_WORKFLOW.md) maps those interfaces.
Pass `RiskFactor` and a positive admissible bump to `sensitivity`; units/transformations
for all seven factor kinds appear in [risk methodology](../methodology/XVA_SENSITIVITIES.md).
No JSON financial request handler or automatic market calibration is added.

Run twice on the same pinned source/runtime to compare stdout. Preserve original
inputs and the source/environment alongside hashes. Safe workflow logs in this
example use an explicitly owned in-memory stream. No network/database/RNG globals
are initialized by importing the modules.

Before interpreting a result, read [unilateral credit](../methodology/XVA.md) and
[additive funding/IM limits](../methodology/FUNDING_MARGIN.md). Default-conditioned
freeze/MPOR, bilateral recursion, regulatory IM and capital remain outside this
phase. [Phase 7 evidence](../validation/phase-7.md) records actual verification.
