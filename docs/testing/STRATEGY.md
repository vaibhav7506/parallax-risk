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
generates bounded property examples and replay tests inject fixed metadata. Future
sequence/Monte Carlo tests will require explicit algorithms/streams/seeds when implemented.
See [benchmarking](../validation/BENCHMARKING.md) and
[sensitivity](../validation/SENSITIVITY.md) for deliberate numerical tolerances.

Phase 2 recorded 333 tests/99.07% coverage on two platforms. That is historical
evidence, not a new test count for documentation-only maintenance. Hosted CI is
configured but has not been observed executing. Performance harness/studies, model
path convergence, mutation and adversarial testing are DEFERRED; no throughput claim exists.

[Phase 3 evidence](../validation/phase-3.md) records the new actual runs separately.
Model steps consume supplied shocks; tests do not implement the deferred path engine.
Synthetic parameter recovery cannot establish production-market validity. Heston
quadrature tolerance, Gaussian/ODE and low-xi cases target different numerical risks.

After Docker-backed checks, retain necessary outputs and remove only the disposable
project verification stack, including on failures; see [cleanup](../operations/DOCKER.md).
