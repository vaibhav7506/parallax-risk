# Components and ownership

| Component | Owns | Does not own |
|---|---|---|
| common | Finite scalar/date/currency primitives, exact Money operations, nominal IDs, errors, hashes, isolated logging | Pricing rules, HTTP, settings loading, persistence |
| domain/market | Immutable observations/snapshots and declared curve representations/construction | Vendor integration, HTTP/Pydantic, model calibration surfaces |
| domain/instruments | Supported contracts and caller-supplied schedules/sign rules | Official calendar/index inference or portfolio aggregates |
| domain/pricing | Discounted signed payments, assumptions/evidence and central sensitivities | Database, environment settings, stochastic paths |
| domain/models | Finite process coefficients/one-step schemes, correlation and analytical/Fourier instrument values | RNG, paths, market vendors or web handlers |
| domain/calibration | Sourced immutable objective/bounds/settings/result and uncertainty contracts | Optimizer initialization, persistence or HTTP validation |
| application | Pydantic input/settings boundaries, run envelope, injected pricing/calibration/simulation/portfolio workflows and ports | ORM models or web handlers |
| infrastructure | SQLAlchemy connectivity and SciPy bounded optimizer adapter | Financial instrument formulas, automatic migrations or governance tables |
| API/CLI | Operational composition, response/exit states and resource cleanup | Financial HTTP jobs, model calculations or approvals |
| scripts/tests/docs | Reproduction, maintenance, independent checks and learning/evidence | Alternate untested financial implementations |

The [code guide](../CODEBASE_GUIDE.md) links principal classes/files and call paths.
The same domain values serve pure Python research and future authorized boundaries;
dependency injection limits hidden process state.

Phase 4 `domain/simulation` owns sequence generation, time grids, vectorized kernels,
Gaussian covariance, immutable buffers, observables and statistical math.
Application owns injected simulation/research orchestration and measured benchmarks.
Notebook dependencies are development-only; they are excluded from the runtime lock
and production image. All notebooks call production experiment modules.

Phase 5 `domain/portfolio` owns legal/lifecycle contracts, CSA conventions, cash ledgers,
FX/haircut/netting mathematics, effective margin calls and deterministic MPOR. The
application PortfolioPricer port/service owns pricing orchestration and validated result
lineage. It composes existing instruments/pricing, without API financial logic or ORM.
See [portfolio workflow](../workflows/PORTFOLIO_WORKFLOW.md).

Phase 6: `domain/exposure` owns conditional contexts, CreditScenario and profile/EAD mathematics; `domain/credit` owns hazard/survival/default and spread policies. `application/exposure.py` composes the existing SimulationEngine and PortfolioService with a market-provider protocol.
See [exposure workflow](../workflows/EXPOSURE_WORKFLOW.md).

Phase 7: `domain/xva` owns funding/margin/result contracts, credit/funding calculators
and numerical sensitivity/attribution. `application/xva.py` injects XvaCalculator and
links exact exposure evidence; `application/xva_revaluation.py` composes full actual
revaluation and admissible named transformations. Examples/scripts own safe composition.

The domain/ccr package owns immutable supervisory inputs, supported contract mapping, standardized formulas, challenger averages and comparison arithmetic. Application CcrService owns legal-unit replay and evidence checks; existing ExposureService/PortfolioService supply actual paths/prices.
[CCR workflow](../workflows/CCR_WORKFLOW.md), [decisions](../decisions/README.md).

## Phase 9 lab scope

Domain validation owns comparable metrics/findings, numerical checks, independent credit benchmarks, bootstrap and covariance mathematics. Application validation owns model ports, actual production adapters, bounded parameter/calibration workflows and sourced stress revaluation. The synthetic composition uses the existing infrastructure solver explicitly.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 applicability

MutationModel and SearchOptimizer are injected ports. Operation probes isolate faults from production; search-model adapters compose actual XVA/exposure and independent credit quadrature. Diagnostic workflows evaluate real repeated endpoints and ordered cases.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).

## Phase 11 applicability

Added domain/governance values/monitoring, application governance ports/codec/
reports/governed XVA/demo composition, and infrastructure PostgreSQL repository
plus frozen migrations. Existing financial engines are reused; no new financial
HTTP route, persistent numerical-input store or monitoring scheduler is deployed.

[Governance contracts](../methodology/GOVERNANCE.md), [actual phase evidence](../validation/phase-11.md).
