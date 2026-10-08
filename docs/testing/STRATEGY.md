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
| API | Operational success/readiness/lifecycle/redaction behavior in tests/api |
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
mutation/adversarial testing and production throughput SLOs are DEFERRED.

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
