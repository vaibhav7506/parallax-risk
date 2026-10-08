# Data and evidence flow

Source-labelled JSON → MarketSnapshotInput → frozen MarketSnapshot. Supplied curve
conventions/knots or supported bootstrap quotes → immutable curves → CurveSet.
Contract/schedule + PricingContext → DiscountingEngine → signed cash-flow PVs and
PricingResult. PricingService attaches RunContext and safe outcome logs.

Observations remain distinct from derived curves: an index fixing records a known
rate, whereas a projection curve supplies a future implied rate. A bump creates new
curve/snapshot values, so base/up/down evidence can identify changed inputs.

```mermaid
flowchart LR
    INPUT[Market payload] --> VALID[Boundary validation]
    VALID --> SNAP[Snapshot + source/hash]
    KNOTS[Explicit curve inputs] --> CURVE[CurveSet + hash]
    TRADE[Supported contract + hash] --> ENGINE[Pricing engine]
    SNAP --> ENGINE
    CURVE --> ENGINE
    ENGINE --> FLOW[Signed original payments and PV contributions]
    FLOW --> RESULT[NPV and assumptions/model evidence]
    RUN[RunContext] --> WRAP[PricingRunResult]
    RESULT --> WRAP
```

Concrete mapping and failure conditions: [workflow](../WORKFLOW.md) and
[pricing call path](../workflows/PRICING_WORKFLOW.md). There is no database write of
these results or persisted calibration/portfolio/governance lineage.

CalibrationRequest → sourced immutable objective/bounds/settings → CalibrationService
with injected ScipyLeastSquares → model predictions and scaled residual optimization
→ CalibrationResult/ParameterUncertainty → run-linked CalibrationRunResult. Quote order,
units, signed residuals, IDs and data/settings hashes remain explicit. This evidence is
in memory/JSON, without persistence. See [calibration path](../workflows/CALIBRATION_WORKFLOW.md).

SimulationRequest + explicit model/unit/measure/sequence/grid/correlation → owned
NormalStream → per-step Gaussian innovation covariance → vectorized transition
→ immutable batch → injected observable → descriptive moments and independent-unit
Estimate or explicit absence → RunContext/SimulationMetadata/result evidence.
Independent Sobol replicates and separate pilot controls retain their own addresses.
The simulation workflow does not write research results or aggregate portfolio exposure.

Phase 5: frozen legal book + dates/position/CSA terms + cash movement ledgers →
PortfolioService → existing deterministic pricer → verified instrument/market/curve
hashes → within-set FX/gross/net/settled-collateral results and pending-aware calls →
separate counterparty risk sums → PortfolioResult/RunContext with ledger/book hashes.
No auto-settlement or pathwise exposure/default/XVA is attached to this flow.
See [portfolio path](../workflows/PORTFOLIO_WORKFLOW.md).

Phase 6: request/book/bindings/fixings/accounts/credit/RunContext → owned addressed market/default draws → path-specific future contexts and cash → PortfolioService → positive/negative matrices → empirical profile, survival and grid EAD. Result hashes preserve inputs and ordered generated markets; no database lineage is added.
See [exposure workflow](../workflows/EXPOSURE_WORKFLOW.md).
