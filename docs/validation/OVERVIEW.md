# Development checks and model validation

Model development implements a calculation; model validation challenges its
mathematics, data assumptions, numerical behavior and appropriate use. Current
independent analytical/integral/ODE software tests support pricing and model primitives; they are
not an institutional model approval, challenger-model lab or governance workflow.

| Current technique | Defect it targets | Evidence |
|---|---|---|
| Independent formulas | Sign, discount ratio, coupon/accrual mistakes | [Benchmarking](BENCHMARKING.md) |
| Invariants/property checks | Scaling, positivity, direction, justified monotonicity | tests/property/test_deterministic_invariants.py |
| Sensitivity comparisons | Incorrect bump units/scope/sign or missing settlement conversion | [Sensitivity](SENSITIVITY.md) |
| Reconciliation/replay | Lost flows, mutable inputs or inconsistent metadata | Quantitative and workflow integration tests |
| Rejection/regression checks | Hidden fallbacks, invalid inputs or numerical failures | tests/unit and tests/regression |

Actual bounded optimizer diagnostics, local parameter uncertainty and supplied-step
refinement are now implemented. See [calibration](../methodology/CALIBRATION.md)
and [Phase 3](phase-3.md). Stress/uncertainty propagation, challenger
models, mutation/adversarial detection matrices, backtesting and governance monitoring
are NOT IMPLEMENTED. Do not invent measured detection rates or model accuracy claims.
Create their detailed documents only with their authorized implementations.

Actual phase outcomes are [Phase 1](phase-1.md), [Phase 2](phase-2.md) and
[Phase 3](phase-3.md) and [Phase 4](phase-4.md). Between-phase
documentation maintenance is [separately recorded](documentation-maintenance.md).

Phase 4 adds known distributions/moments, exact Gaussian covariance reproduction,
scalar/vector reconciliation, batch replay, antithetic counterexamples, separate control
pilots, independent-scramble intervals and multi-replicate convergence comparisons.
[The benchmark methodology](MONTE_CARLO_BENCHMARKS.md) separates measured timings,
buffer sizes and traced allocation scope from deployment capacity claims.
