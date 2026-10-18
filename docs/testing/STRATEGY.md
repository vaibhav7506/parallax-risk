# Test strategy and evidence

Ordinary software tests check behavior and failure paths; quantitative tests also
challenge mathematical results against independent targets within stated units and
tolerances. Coverage is a guard against untested paths, not proof of model correctness.

| Suite | Purpose / files |
|---|---|
| Unit | Primitives, settings, frozen snapshots, curves/bootstrap/contracts/results and range failures in tests/unit |
| Property | Bounded mathematical invariants in tests/property; monotonicity only under nonnegative flat rates |
| Quantitative | Independent Decimal/formula targets and cash-flow/parity reconciliation in tests/quantitative |
| Regression | Missing fixing/projection, paid-flow cutoff and extreme annuity guards in tests/regression |
| Integration | Real PostgreSQL/CLI, import/layer safety, package metadata and synthetic workflow replay in tests/integration |
| API | Operational and financial guard/auth/rate/body/CORS/lifecycle/redaction behavior in tests/api; real persisted workflows in tests/integration/test_service_postgres.py |
| Documentation/operations | Local links/references/index/ADR reviews and ownership-checked cleanup scripts |
| Phase 3 model/calibration | Independent Gaussian-integral/Riccati-ODE targets, exact/Euler refinement, recovery/replay, bounds/failures/identification and strict source/input guards |

`python -m pytest` enables branch-inclusive coverage with a >=95% gate. Supply
`PARALLAX_TEST_DATABASE_URL` for the isolated live PostgreSQL test; a skip must be
reported. Use `python -m ruff check .`, format check and strict mypy for production
typing/style. [Development](../../DEVELOPMENT.md) lists exact commands.

The existing deterministic suites do not consume random model draws; Hypothesis
generates bounded property examples and replay tests inject fixed metadata. Phase 4
sequence/Monte Carlo tests specify algorithms, stream addresses, transforms and seeds.
See [benchmarking](../validation/BENCHMARKING.md) and
[sensitivity](../validation/SENSITIVITY.md) for deliberate numerical tolerances.

Phase 2 recorded 333 tests/99.07% coverage on two platforms. That is historical
evidence, not a new test count for documentation-only maintenance. Hosted CI is
configured but has not been observed executing. Phase 4 adds a measured research harness and multi-replicate path convergence;
Phase 10 implements scoped mutation/adversarial testing; production throughput SLOs remain DEFERRED.

[Phase 3 evidence](../validation/phase-3.md) records the new actual runs separately.
Scalar model steps consume supplied shocks; Phase 4 tests exercise the separate path engine.
Synthetic parameter recovery cannot establish production-market validity. Heston
quadrature tolerance, Gaussian/ODE and low-xi cases target different numerical risks.

After Docker-backed checks, retain necessary outputs and remove only the disposable
project verification stack, including on failures; see [cleanup](../operations/DOCKER.md).

Phase 4 tests require distribution mean errors within six analytical standard errors,
deliberate variance/correlation tolerances, scalar/vector `atol=rtol=1e-12` benchmarks
(and tighter ordinary-range reconciliation), and exact pinned-environment batch replay.
Convergence slopes are checked across 32 independent replicates with broad statistical
bounds, without demanding monotonic improvement in a single run. Antithetic inference
is checked on pair averages and an even-function counterexample. Sobol intervals use
replicates, never points. Both notebooks execute in the project kernel. Actual final
counts/environments appear in [Phase 4 evidence](../validation/phase-4.md).

Phase 5 adds exact decimal threshold/MTA/ledger checks, independent FX discount-ratio
targets (relative tolerance 1e-14), legal-scope/lifecycle/injected-pricer reconciliation,
80 generated netting-bound/collateral-monotonicity cases and deterministic MPOR freezes.
No synthetic data is represented as observed or regulatory. Full platform/count/coverage
evidence appears in [Phase 5](../validation/phase-5.md).

Phase 6 targets: piecewise hazard identities/inversion (1e-15), known default CDFs
within six binomial standard errors, constant spread equivalence, dynamic dependence
under preserved credit marginals, linear empirical quantiles and trapezoidal EPE.
Actual FX-forward future EE is checked against the analytic lognormal positive part
within six sample standard errors. Sixty generated PFE/collateral properties assert
only justified monotonicity. Workflow checks exercise lifecycle, daily cash settlement,
known-fixing retention, conditional HullWhite knots (relative 1e-14), malformed adapters,
unique random addresses and exact pinned-environment batch/replay behavior.
Full tests must include live PostgreSQL and >=95% branch-inclusive coverage. See
[Phase 6 results](../validation/phase-6.md); historical totals are not relabelled.

Phase 7 checks independent constant-exposure CVA/DVA targets, zero PD/full recovery/
zero exposure, piecewise funding knots, external IM separation, sign/component
reconciliation and no duplicate PD in sampled loss. Discounted credit quadrature
refinement has a closed-form target and second-order error-ratio check. Generated
constant-exposure hazard/recovery properties assert only justified monotonicity.

Actual-path tests cover all seven factor types, selected h/h2 stability, preserved
stream addresses, separate entity aggregation, custom/shared-credit policy rejection,
stale calculator evidence, five retained valuations and complete/omitted movement
residuals. Guard suites challenge malformed currency/grid/types/hashes/nonfinite and
unsupported bumps. Full live PostgreSQL/platform/coverage outcomes appear in
[Phase 7 evidence](../validation/phase-7.md). Historical totals remain unchanged.

## Phase 8 CCR checks

Independent formula/CRE99 RC targets, duration/maturity floors, IR bucket and FX
pair offsets, signed collateral/NICA, multiplier limits, cap and homogeneous
trade/CSA scaling are tested. Effective EE/EPE targets use explicit unequal grids
and exact horizon nodes. Actual deterministic MC FX exposures have an independent
closed form; legal units, daily margin, batch replay and stale evidence are checked.
Capital/exception/bridge semantics and unsupported/numerical input ranges reject.
All new absolute monetary assertions explicitly set rel=0. Full phase validation
requires both platforms, live isolated PostgreSQL and >=95% branch-inclusive
coverage. [Actual evidence](../validation/phase-8.md); [workflow](../workflows/CCR_WORKFLOW.md).

## Phase 9 lab scope

Phase 9 adds independent constant/linear-exposure credit targets, production grid-bias detection and refinement, zero/scaling/fixed-cash invariants, finite-difference checks, owned bootstrap replay, covariance cross-term targets, actual path/grid XVA studies, sourced stress adapter and invalid boundary tests. Full release acceptance retains >=95% branch-inclusive coverage; focused tests alone are not whole-package coverage evidence. See `tests/quantitative/test_validation_lab.py`, `tests/unit/test_validation_guards.py` and `tests/integration/test_validation_workflow.py`.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 checks

`tests/quantitative/test_adversarial_lab.py` tests all 15 independent operation
observables, one-fault isolation, weak/equivalent misses, baseline qualification,
known bounded/constraint optima, owned replay and forensic arithmetic residuals.
`tests/unit/test_adversarial_guards.py` checks malformed economic/time/provenance
inputs, reserved names, budgets, stale/schema changes, fabricated check/result
states, infeasible populations and preserved valuation errors.
`tests/integration/test_adversarial_workflow.py` exercises actual XVA quadrature,
all six requested search factors on a valid daily CSA baseline and canonical JSON.

An optimizer stopping short of a known constrained optimum under a small population
is recorded in [Phase 10 evidence](../validation/phase-10.md). More search effort is
not proof of global optimality. Actual whole-package coverage and live database
results are recorded separately; focused coverage is not whole-release evidence.

## Phase 11 applicability

New contract/state/codec tests reject malformed evidence, nonfinite measurements,
wrong units/scopes, invalid lifecycle transitions and stale revisions. Live
PostgreSQL tests create and finally drop only their own UUID schemas in the
explicitly isolated test DB; they exercise zero/repeated migration, destructive
opt-in reversal, append-only triggers, atomic rollback, reference guards, concurrent
CAS and privileged-tamper detection. Actual governed XVA and all seven reports
are exercised. A skipped DB case is not live verification. Coverage measures
execution, not financial validity; read the Phase 11 report for actual platform/results.

[Governance contracts](../methodology/GOVERNANCE.md), [actual phase evidence](../validation/phase-11.md).
