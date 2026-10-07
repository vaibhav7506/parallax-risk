# Domain relationships and financial ownership

Contracts describe payments owed; snapshots describe what is known; curves describe
discounting/projection assumptions; results preserve the evidence tying them together.
These are separate values because changing a model curve should not change the
observed fixing or the contractual obligation.

```mermaid
classDiagram
    MarketSnapshot "1" *-- "many" SourceLabelledObservation
    CurveSet "1" *-- "many" DiscountCurve
    CurveSet "1" *-- "many" ForwardCurve
    ForwardCurve --> DiscountCurve : projection representation
    PricingContext --> MarketSnapshot
    PricingContext --> CurveSet
    Instrument --> Money : explicit units and currency
    Instrument --> AccrualPeriod : supplied schedule
    PricingResult "1" *-- "many" CashFlowPresentValue
    PricingRunResult --> PricingResult
    PricingRunResult --> RunContext
    CalibrationProblem "1" *-- "many" SourcedInstrumentObservation
    CalibrationResult "1" *-- "many" ParameterBound
    CalibrationResult --> ParameterUncertainty
    CalibrationRunResult --> CalibrationResult
    CalibrationRunResult --> RunContext
```

`SourceLabelledObservation` and `Instrument` summarize several concrete types in the
diagram; they are not additional instantiated classes. MarketSnapshot owns tuples of
quotes/rates/FX/volatility/credit/fixings. CurveSet owns unique discount and index
projection assignments and rejects a CurveId reused for inconsistent contents.

CashFlow/FixedRateCashFlow/FloatingRateCashFlow use signed notionals/amounts. Bond
face, swap notional and FX base notional are nonnegative; explicit directions create
the signs of exchanged payments. AccrualPeriod separates accrual from payment dates
because lagged payments change discounting. An index name identifies the required
fixing/projection convention; the code does not fabricate an official market index.

PricingResult owns original signed amounts, reporting-currency contributions and
input hashes. RunContext identifies a workflow/configuration; it is not a persisted
risk job, model approval or random generator. Phase 5 wraps nominal identities in
actual immutable legal portfolio aggregates.

ExposureProfile, XVAResult, Finding and persisted model-governance aggregates are
NOT IMPLEMENTED. Deterministic current portfolio risk is separate from a future
stochastic exposure profile.
See [roadmap](../ROADMAP.md), [code locations](CODEBASE_GUIDE.md) and
[limitations](LIMITATIONS.md).

SourcedInstrumentObservation summarizes DiscountObservation, BondOptionObservation
and CallObservation; it is not another concrete class. CalibrationProblem is a protocol
implemented by three immutable Q-model objectives. Premium inputs are separate from
MarketSnapshot volatility observations. CalibrationResult owns bounds/fitted values,
predictions/residuals/status/hashes and ParameterUncertainty; the application wraps
it with RunContext. It is not a persisted calibration job or an approval.

Vasicek/HullWhite/GeometricBrownianMotion/Heston implement finite coefficient
contracts; state is an immutable tuple, not a path aggregate. CorrelationMatrix owns
factor order and values. CorrelationRepair preserves the explicitly requested
transformation evidence. See [model contracts](methodology/STOCHASTIC_PROCESSES.md)
and [calibration](methodology/CALIBRATION.md).

Phase 4 adds SimulationRequest → ProcessComponent/TimeGrid/SequenceSpec/CorrelationMatrix,
MonteCarloEngine → immutable PathBatch/FrozenArray, and SimulationService →
SimulationRunResult/SimulationMetadata/RunContext. Estimate separates raw path moments
from independent sampling units. ReplicatedSobolResult owns independently addressed
complete designs and scramble-mean inference. ControlVariate preserves a separate
pilot key, observation count, coefficient and known expectation. These are research
values, not persistent jobs, portfolios or exposure profiles.
See [simulation](methodology/MONTE_CARLO.md) and [statistics](methodology/MONTE_CARLO_STATISTICS.md).

## Phase 5 book and collateral relationships

```mermaid
classDiagram
    PortfolioSnapshot "1" *-- "many" Counterparty
    Counterparty "1" *-- "many" NettingSet
    NettingSet "1" *-- "many" Trade
    Trade --> Instrument : signed quantity and lifecycle
    NettingSet --> Csa : optional scoped agreement
    CollateralAccount --> NettingSet : typed scope ID
    CollateralAccount --> Csa : typed agreement ID
    CollateralAccount "1" *-- "many" CollateralMovement
    PortfolioResult --> CounterpartyResult
    CounterpartyResult --> NettingResult
    NettingResult --> MarginCall
    PortfolioResult --> RunContext
```

`src/parallax_risk/domain/portfolio/contracts.py` owns the immutable snapshot and
legal hierarchy; `csa.py` owns eligible cash/threshold/direction/calendar conventions.
`collateral.py` owns physical cash history, effective calls and MporScenario; `netting.py`
owns TradeValue/NettingResult. `src/parallax_risk/application/portfolio.py` owns the
injected PortfolioPricer workflow and result envelope. Each set retains separate
risk and collateral; counterparty/portfolio risk sums do not create new legal netting.
See [formulas and limitations](methodology/PORTFOLIO_COLLATERAL.md).
