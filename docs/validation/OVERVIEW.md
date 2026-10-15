# Development checks and model validation

Model development implements a calculation; model validation challenges its
mathematics, data assumptions, numerical behavior and appropriate use. Current
independent analytical/integral/ODE software tests support pricing and model primitives; they are
not institutional model approval or a governance workflow. Phase 9 now adds a library challenger-model lab.

| Current technique | Defect it targets | Evidence |
|---|---|---|
| Independent formulas | Sign, discount ratio, coupon/accrual mistakes | [Benchmarking](BENCHMARKING.md) |
| Invariants/property checks | Scaling, positivity, direction, justified monotonicity | tests/property/test_deterministic_invariants.py |
| Sensitivity comparisons | Incorrect bump units/scope/sign or missing settlement conversion | [Sensitivity](SENSITIVITY.md) |
| Reconciliation/replay | Lost flows, mutable inputs or inconsistent metadata | Quantitative and workflow integration tests |
| Rejection/regression checks | Hidden fallbacks, invalid inputs or numerical failures | tests/unit and tests/regression |

Actual bounded optimizer diagnostics, local parameter uncertainty and supplied-step
refinement are now implemented. See [calibration](../methodology/CALIBRATION.md)
and [Phase 3](phase-3.md). Phase 9 implements scoped stress/uncertainty propagation and comparable challenger models.
Phase 10 implements scoped mutation detection evidence and bounded adversarial search. Backtesting and governance monitoring remain NOT IMPLEMENTED. Do not generalize selected-probe rates or invent model accuracy claims.
Create their detailed documents only with their authorized implementations.

Actual phase outcomes are [Phase 1](phase-1.md), [Phase 2](phase-2.md) and
[Phase 3](phase-3.md) and [Phase 4](phase-4.md). Between-phase
documentation maintenance is [separately recorded](documentation-maintenance.md).

Phase 4 adds known distributions/moments, exact Gaussian covariance reproduction,
scalar/vector reconciliation, batch replay, antithetic counterexamples, separate control
pilots, independent-scramble intervals and multi-replicate convergence comparisons.
[The benchmark methodology](MONTE_CARLO_BENCHMARKS.md) separates measured timings,
buffer sizes and traced allocation scope from deployment capacity claims.

Phase 5 checks current deterministic portfolio/netting/collateral risk, pending-aware
margin instructions, physical FX/haircuts, lifecycle and explicit MPOR endpoints. It
does not validate a stochastic exposure/default model. See [Phase 5](phase-5.md).

Phase 6 checks actual pathwise repricing and empirical exposure/credit policies with
independent analytical targets, default distributions, justified properties and
preserved-marginal WWR experiments. These are software/model mathematics checks,
not external calibration, independent institutional approval or regulatory validation.
[Phase 6 results](phase-6.md), [method assumptions](../methodology/EXPOSURE.md).

Phase 7 adds independently targeted unilateral XVA, transparent funding/IM proxies,
actual central revaluation and residual reconciliation. Validation retains mathematical
and sampling limitations; it does not establish bilateral pricing, regulatory IM or
production model approval. [Phase 7 evidence](phase-7.md),
[formulations](../methodology/XVA.md), [risk](../methodology/XVA_SENSITIVITIES.md).

Phase 8 compares a restricted standardized prototype with actual per-legal-unit
Monte Carlo effective EE/EPE. Independent formula/RC and deterministic exposure
targets, scaling/netting/collateral checks and report exceptions verify implemented
behavior. This is not independent institutional approval or full regulatory
compliance. [Phase 8 evidence](phase-8.md),
[methodology](../methodology/STANDARDIZED_CCR.md).

Phase 9 adds immutable findings, automatic invariants, actual production/challenger
comparison and numerical/uncertainty/stress workflows. [Methods](../methodology/MODEL_VALIDATION.md),
[workflow](../workflows/VALIDATION_WORKFLOW.md), [actual evidence](phase-9.md).

## Phase 10 lab scope

Controlled faults execute selected actual validations and retain missed mutants.
Bounded searches retain same-case paired outputs/status; actual repeat/counterfactual
forensics retains materiality and residual. These remain research evidence, not
model approval. [Methods/workflow](../workflows/ADVERSARIAL_WORKFLOW.md).
