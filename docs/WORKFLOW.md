# Implemented and planned workflow

```mermaid
flowchart TD
    JSON[Labelled market input] --> VALID[Pydantic validation]
    VALID --> SNAP[Immutable snapshot]
    SNAP --> CURVES[Explicit curve construction and assignment]
    CONTRACT[Contract and supplied schedule] --> PRICE[Deterministic pricing]
    SNAP --> PRICE
    CURVES --> PRICE
    RUN[Run metadata] --> SERVICE[Injected pricing service]
    SERVICE --> PRICE
    PRICE --> RESULT[NPV, cash flows, assumptions and hashes]
    RESULT --> RISK[Central zero-knot PV01 and FX delta]
    CALJSON[Sourced instrument quotes and bounded parameters] --> CAL[CalibrationService / SciPy]
    CAL --> MODELS[Stochastic model instrument predictions]
    MODELS --> FIT[Parameters, residuals, identification and hashes]
    FIT -.-> CONFIG[Explicit caller model/configuration choice]
    CONFIG --> MC[SimulationService / batched research paths]
    MC --> STATS[Independent-unit estimates and convergence evidence]
    RESULT --> BOOK[PortfolioService / legal netting and settled collateral]
    BOOK --> CURRENT[Current risk and pending-aware margin instruction]
    MC --> EXP[ExposureService / pathwise exposure and credit]
    BOOK --> EXP
    EXP --> XVA[XvaService / unilateral credit and additive funding]
    XVA --> XRISK[Actual central differences and movement residuals]
    EXP --> CCR[CcrService / legal-unit standardized and IMM comparison]
    CCR --> COMP[EAD, illustrative capital, driver bridge and exceptions]
    XVA --> LAB[Validation lab: models, findings, uncertainty, stresses]
    LAB -.-> GOV[PLANNED: governance]
```

| Implemented step | Input / transformation / output | Module and failure |
|---|---|---|
| Ingestion | JSON with explicit dates, values and provenance → checks → immutable snapshot | application/market_data + domain/market; malformed/duplicate/missing metadata errors |
| Curves | Explicit knots/quotes, conventions and assignments → interpolation/bootstrap → discount/projection curves | domain/market/curves; invalid anchor/horizon/root/residual errors |
| Contracts | Money + supplied schedules/day counts/directions → checks → typed instrument | domain/instruments; invalid schedule/notional/convention errors |
| Run orchestration | Context + instrument + frozen run envelope → safe logs/injected engine → run-linked result | application/pricing; propagates authored errors |
| Pricing | Future signed payments → historical fixing or projected rate → discounted PV contributions | domain/pricing; missing fixing/index/currency/FX or numerical failure |
| Sensitivity | Explicit curve IDs/spot bumps → immutable up/down revaluation → central derivative/evidence | domain/pricing/sensitivities; invalid/resolution/range failure |
| Calibration | Sourced premiums + explicit model/bounds/scales → injected bounded optimizer → convergence/parameters/uncertainty/evidence | application/calibration + infrastructure/calibration + domain models/objectives; explicit failures |
| Model step | Finite state/time/independent shocks → chosen exact or numerical scheme → next state | domain/models; no RNG, invalid states/proposals fail, Heston projection is reported |

See [code call path](CODEBASE_GUIDE.md) and [pricing workflow](workflows/PRICING_WORKFLOW.md).
See [calibration workflow](workflows/CALIBRATION_WORKFLOW.md) and
[simulation workflow](workflows/SIMULATION_WORKFLOW.md). Future arrows describe
intended phases. Phase 7 adds signed XVA/risk; Phase 8 adds restricted CCR comparisons. Governance remains absent.

Phase 4: explicit typed simulation configuration + RunContext → owned addressed
normal stream → corrected Gaussian driver covariance → selected vectorized kernels
→ immutable path batches → observable → independent-unit moments/inference and
convergence evidence. Single Sobol designs record absent IID inference; independent
scramblings provide valid sampling units. Separate control pilots are never implicitly
fitted on the evaluation stream.

Phase 5: immutable book + matching PricingContext + complete scoped cash ledgers +
RunContext → injected pricer/lineage validation → within-set gross/net value → settled
collateral residual/current risk and pending-aware instruction → positive/negative set
risk sums across legal entities. A separate deterministic MPOR scenario freezes settled
physical cash and values it at caller-supplied closeout. See
[portfolio workflow](workflows/PORTFOLIO_WORKFLOW.md).

Phase 6: SimulationRequest + conditional market binding + legal book + initial ledgers
+ optional credit scenarios + RunContext → owned market/default sequences → path-local
future markets/fixings/cash → PortfolioService repricing → retained positive/negative
paths → EE/ENE/PFE/EPE and separately labelled grid EAD/survival comparisons.
See [exposure workflow](workflows/EXPOSURE_WORKFLOW.md).

Phase 7: matching exposure/credit + own credit + deterministic origin discount +
funding excess spreads + external posted IM → injected calculator → per-name signed
CVA/DVA/FVA/MVA and aggregate adjustment. Actual exposure is rerun at admissible factor
shifts with fixed sequence addresses → component central differences/stability;
ordered exact movements + independently valued actual endpoint → explicit residuals.
See [XVA workflow](workflows/XVA_WORKFLOW.md). Funding/IM remain fixed during listed
bumps; default-conditioned/bilateral and recursive economics are not inferred.

Phase 8: explicit supervisory/comparison configuration + matching simulation/book/
conditional markets/run + scoped ledgers/business-day margin terms → actual
per-legal-unit repricing → restricted standardized and effective-EE/EPE challenger
→ EAD/capital-input comparison, arithmetic driver bridge/residual and strict
exceptions. No financial HTTP job or regulatory approval is inferred.
See [CCR workflow](workflows/CCR_WORKFLOW.md).

Phase 9: immutable case + injected comparable models + explicit unit/tolerance policy
→ actual outputs/component differences/residuals → checks and immutable findings.
Actual local perturbations and path/grid revaluations → sensitivity/convergence evidence;
independent units, supplied ensembles or available calibration covariance → distinctly
labelled selected-risk bands. Sourced ordered scenarios → actual stress results.
[Validation workflow](workflows/VALIDATION_WORKFLOW.md). No approval or persistence is inferred.
