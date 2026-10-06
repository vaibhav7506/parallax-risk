# Parallax Risk codebase guide

The code currently supports primitives, operational service checks and deterministic
pricing, stochastic model primitives and instrument calibration. [Roadmap](../ROADMAP.md)
marks later capabilities NOT IMPLEMENTED.

| Package | Purpose / principal objects | Inputs → outputs; caller/dependencies |
|---|---|---|
| `src/parallax_risk/common/` | Money, typed IDs, dates/conventions, finite arithmetic, hashes, safe logs/errors | Explicit primitive values → validated values/errors; used inward by all layers |
| `src/parallax_risk/domain/market/` | SourceMetadata, MarketSnapshot and observation types | Typed observations → immutable hashed daily snapshot; called by ingestion, consumed by pricing |
| `src/parallax_risk/domain/market/curves/` | DiscountCurve, ZeroCurve, ForwardCurve, CurveSet; bootstrap and diagnostics | Declared knots/conventions/quotes → curves, forwards, residuals; common math only |
| `src/parallax_risk/domain/instruments/` | CashFlow, FixedRateCashFlow, FloatingRateCashFlow, bonds, swaps, FxForward | Explicit Money/schedules/direction → immutable contracts; no vendor/calendar inference |
| `src/parallax_risk/domain/pricing/` | PricingContext, DiscountingEngine, PricingResult; sensitivities | Contracts + snapshot/curves → reconciled signed PV/evidence; no HTTP/ORM |
| `src/parallax_risk/domain/models/` | Vasicek, HullWhite, GeometricBrownianMotion, Heston, schemes, correlation and Heston calls | Parameters/state/time/shocks → coefficients/transitions or analytical instrument price; NumPy/SciPy numerical math only |
| `src/parallax_risk/domain/calibration/` | Sourced objectives, bounds/settings/results/uncertainty | Immutable instrument data/parameters → predictions and finite evidence contracts |
| `src/parallax_risk/infrastructure/calibration/` | ScipyLeastSquares | Implements application solver port; objective/bounds → result or explicit error |
| `src/parallax_risk/application/` | Settings, RunContext, MarketSnapshotInput, PricingService, ConnectivityProbe | Boundary/env data → validated domain inputs/run-linked results/port contracts |
| `src/parallax_risk/infrastructure/persistence/` | PostgresConnectivity | Configured URL → SELECT 1 or sanitized error; implements application port |
| `src/parallax_risk/api/` | create_app, operational schemas | GET health/readiness/version → JSON/status; owns probe lifespan |
| `src/parallax_risk/cli/` | main | version/config/run-context/check-db args → JSON or safe error/exit status |
| `scripts/` | Synthetic example, lock snapshot, docs validator, scoped cleanup | Local reproducible/maintenance workflows; no new financial HTTP commands |

## End-to-end pricing call path

1. `scripts/demo_deterministic.py` reads the fixed synthetic JSON to teach a complete
   workflow without calling a vendor or implementing formulas in a notebook.
2. `src/parallax_risk/application/market_data.py`: `MarketSnapshotInput.model_validate_json()`
   checks boundary types/dates/provenance, and `to_domain()` isolates immutable values.
3. `src/parallax_risk/domain/market/curves/term_structures.py`: `ZeroCurve` with explicit
   compounding/day count becomes a separately declared `DiscountCurve` representation;
   `CurveSet` assigns discount currencies and projection indices.
4. `src/parallax_risk/application/pricing.py`: `PricingService.price()` receives a
   typed contract, PricingContext and RunContext, and records safe start/outcome logs.
5. `src/parallax_risk/domain/pricing/engine.py`: `DiscountingEngine.price()` dispatches
   the supported contract, excludes paid flows, generates signed payments, obtains
   mandatory historical fixings or future index forwards, and discounts each payment.
6. `src/parallax_risk/domain/pricing/results.py`: `PricingResult` contains NPV, model
   assumptions and flow/input evidence. The service wraps it as `PricingRunResult`.
7. `src/parallax_risk/domain/pricing/sensitivities.py` revalues explicitly bumped
   immutable inputs for central rate/FX differences, retaining base/up/down prices.

Why each stage exists, failure conditions and financial meaning are expanded in
[pricing workflow](workflows/PRICING_WORKFLOW.md) and [methodology](methodology/PRICING.md).

## Operational path

API `create_app()` / CLI `main()` → explicit settings → injected/lazy PostgreSQL
probe → SELECT 1 → safe status. API lifespan/CLI finally closes the probe. This
is operational connectivity, not a pricing or risk-job workflow.

## How do I change…?

| Change | Existing location/interface | Tests and documentation |
|---|---|---|
| Derivative | Instrument contract in domain/instruments; extend `Instrument` union and `DiscountingEngine.price()` | Independent formula, malformed/cutoff/reconciliation checks; methodology/PRICING and workflow |
| Interpolation | `Interpolator` protocol, `InterpolationKind`, strategy factory in curves/interpolation | Knot/interior/positivity/boundary checks; methodology/CURVES, new/updated ADR |
| Market observation | Immutable observation + snapshot consistency + Pydantic boundary | Snapshot/type/hash/mutation tests; methodology/MARKET_DATA |
| CLI operation | `src/parallax_risk/cli/main.py` composition | Integration exit/redaction/lifetime tests; operations/API docs |
| API operation | `src/parallax_risk/api/app.py` and schemas; avoid numeric logic | API success/failure/startup tests; api/ENDPOINTS |
| Stochastic model | StochasticProcess/ExactProcess/Discretization in domain/models/base; coefficients and explicit scheme | Independent mathematical targets, domains/refinement; model methodology and ADR |
| Calibration objective/solver | CalibrationProblem in domain/calibration/contracts; objective in problems; application CalibrationSolver; infrastructure adapter | Recovery, bounds, optimizer failure and identification; methodology/CALIBRATION and workflow |
| XVA, stress/mutation, governance entity/table | NOT IMPLEMENTED; respective later phases required | Do not invent present folders/classes; update roadmap and new actual interfaces then |

Domain errors are in `src/parallax_risk/common/errors.py`; typed names are in
`src/parallax_risk/common/identifiers.py`. See [testing](testing/STRATEGY.md) for
verification scope and [decisions](decisions/README.md) for the reasoning behind boundaries.

## End-to-end calibration call path

1. `scripts/demo_calibration.py` reads explicitly synthetic instrument JSON, including
   generating parameters, currency, as-of/provenance, quote scales and parameter bounds.
2. `src/parallax_risk/application/calibration_inputs.py`: CalibrationRequest validates
   the selected model/numeric/source boundary; to_domain isolates immutable objectives.
3. `src/parallax_risk/application/calibration.py`: CalibrationService receives objective,
   bounds, solver settings, CalibrationRunId and RunContext; safe logs expose outcome.
4. `src/parallax_risk/infrastructure/calibration/scipy_solver.py`: ScipyLeastSquares
   validates bounds/domains, repeatedly obtains model predictions and fits scaled errors.
5. `src/parallax_risk/domain/calibration/problems.py` dispatches parameter sets to
   analytical rate bonds/bond calls or Fourier Heston calls in `domain/models`.
6. The solver computes raw/scaled metrics, identification and local uncertainty or
   absence; CalibrationResult retains input/settings hashes, fitted parameters and status.
7. The service returns CalibrationRunResult, preserving run metadata. No database or
   RNG is called. See [workflow](workflows/CALIBRATION_WORKFLOW.md) for failure semantics.

## Simulation call path and change locations

`src/parallax_risk/domain/simulation/contracts.py` owns immutable requests, units,
measure/scheme choices, time grid and metadata. `random.py` owns explicitly addressed
sequences; `engine.py` streams immutable batches and normalizes exact OU covariance;
`kernels.py` implements reconciled vectorized transitions. `arrays.py` publishes
immutable buffers. `statistics.py`, `controls.py` and `observables.py` own numerical
estimation and research statistics.

`src/parallax_risk/application/simulation.py` injects the SimulationEngine/PathObservable
contracts, validates complete contiguous output and preserves run/result evidence.
`simulation_research.py` runs path-count and variance comparisons; `simulation_examples.py`
provides labelled synthetic cases, and `simulation_benchmark.py` measures buffers/time.
Scripts and notebooks call these production modules; there is no alternate notebook
pricing formula, persistence adapter or financial HTTP endpoint.

To add a sequence or observable, extend its explicit contract and replay/domain tests.
To add a vectorized model, reconcile against independent scalar/math targets and extend
covariance semantics where required. See [workflow](workflows/SIMULATION_WORKFLOW.md).
