# XVA bump/revalue and ordered movement attribution

Phase 7 recomputes actual exposure and all four XVA components for every bump.
`XvaRevaluation` owns composition; domain sensitivity/attribution functions consume
the resulting immutable values. There is no cached Greek, linear proxy substituted
for repricing, or Shapley allocation.

## Factors and conventions

Each target is an exact component, counterparty, driver pair or legal scope ID.
Bumps are absolute in the input's declared unit. Derivatives are reporting-currency
amount per input unit; multiply an annual-rate/spread derivative by 1e-4 only when
explicitly reporting a one-basis-point movement. No DV01 sign is inferred.

| Kind | Transformation and boundary |
|---|---|
| Rate | Bound Vasicek/HullWhite initial short rate and long-run/initial-forward level shift together; reporting discount zero knots shift for the affected currency. FX drift changes by delta*(affected quote - affected base). Origin fixings stay fixed. Caller must establish initial consistency. |
| FX | Bound direct GBM QUOTE/BASE initial spot shifts; spot must stay positive. |
| Volatility | Declared Vasicek/HullWhite/GBM volatility shifts; parameter stays nonnegative. Heston vega is unsupported and rejected. |
| Credit spread | Existing counterparty baseline hazards shift by delta/(1-R). This is an annual decimal credit-triangle parameter sensitivity, not recalibrated market CS01. For dynamic ReducedFormSpread, initial spread state shifts too. A shared spread component is rejected for a single-name move. |
| Recovery | Counterparty fraction shifts, baseline hazards held fixed. Dynamic ReducedFormSpread is rebuilt with the new recovery; its intensity changes at fixed spread. Generic custom policies cannot be silently transformed and are rejected for credit/recovery bumps. |
| Correlation | Both symmetric off-diagonal entries of an exact Brownian driver pair shift; factor order and existing PSD tolerance are preserved. Missing correlation starts from explicit identity. Range/PSD/singular-engine failures are rejected without repair. |
| Collateral | Existing CSA receive threshold shifts in its currency using Decimal Money. Other terms stay fixed; discrete frequency/lag/eligibility changes have no central-derivative interface. |

The engine uses the same request sequence address, default thresholds and static
rank address at every valuation. Correlation transforms change, while underlying
independent draws retain their addresses. Fixed streams reduce sampling noise;
they do not remove numerical error, exposure kinks or bucketed-default discontinuities.
Funding terms and external IM stay fixed; see [funding limitations](FUNDING_MARGIN.md).

## Finite differences and stability

Five full valuations retain the base and +/-h, +/-h/2 results. For each component
and their total:

```text
g_h = [X(+h)-X(-h)]/(2h)
g_half = [X(+h/2)-X(-h/2)]/h
stability_difference = abs(g_h-g_half)
```

h must be positive and numerically resolved; every bumped input must be admissible
and change input identity. There is no clamping, one-sided fallback or hidden
correlation projection. Stability is reported as actual evidence; no universal
pass threshold or institutional certification is attached. An input can change
while an estimated adjustment stays equal, giving a legitimate zero derivative.

Selected independent FX/credit/recovery cases check theoretical CVA signs and
h/h2 stability. Recovery sign is not imposed on dynamic credit because changing
LGD also changes the specified spread-to-intensity mapping. Neither correlation,
rate nor collateral sensitivity has a universal sign for arbitrary books. Sampled
default loss can be flat or unstable under small bumps even with common draws.

## Attribution and residual

`FactorMove` names a validated absolute movement. `attribute` applies them in the
declared order, revalues each intermediate experiment and independently revalues
the actual endpoint. Each step records four component changes, total change and
before/after result hashes. Names must be unique.

```text
actual-baseline = sum(ordered step movements) + (actual-last ladder result)
```

The final term is always reported, both for each component and the total. It may
capture omitted factors, changed IM/funding, order effects relative to another
allocation, or numerical rounding. Zero residual requires the ladder to reproduce
the actual endpoint; it is not forced. Sequential allocation is order dependent;
interactions are assigned along the chosen path. It is not Shapley or a causal
decomposition. Tests reconcile complete and intentionally incomplete ladders
within 1e-12 currency units.

## Code

`src/parallax_risk/application/xva_revaluation.py`,
`src/parallax_risk/domain/xva/risk.py`, `tests/integration/test_xva_workflow.py`,
`tests/unit/test_xva_contracts.py`.
[Workflow](../workflows/XVA_WORKFLOW.md), [tutorial](../tutorials/06-FIRST-XVA-RUN.md),
[ADR 0019](../decisions/0019-xva-common-stream-risk-attribution.md).
