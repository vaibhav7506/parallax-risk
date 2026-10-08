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
