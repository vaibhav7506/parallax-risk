# Parallax Risk — Phase 4 implementation and verification

**Status:** Complete. **Release:** 0.4.0. Phase 5 remains NOT IMPLEMENTED.

## Requirements and implementation

| Phase 4 requirement | Actual implementation / evidence |
|---|---|
| Pseudo normals, seeds, independent streams/substreams | Explicit PCG64DXSM/SeedSequence addresses, finite Ziggurat normals, allocation-order and replay tests |
| Antithetic variates | Adjacent complete reflected pairs, pair-average inference and an even-function counterexample |
| Sobol quasi-Monte Carlo | Explicit independent scrambling, complete powers of two, no skipped/thinned points, declared finite-bit midpoint normal transform |
| Control variate framework | Separate pilot/frozen coefficient, known expectation, evaluation-key rejection and pilot-cost comparisons |
| Single/correlated multi-factor paths | GBM/Vasicek/Hull–White/Heston components; ordered Brownian correlation with exact Gaussian innovation covariance |
| Time grids, batching, vectorization | Explicit year fractions, immutable path/time/state buffers, batch-size replay and scalar/vector reconciliation |
| Deterministic replay and metadata | Full request/observable hashes, algorithm/transform/layout, runtime/platform, units/measure, optional source revision and RunContext |
| Moments, standard errors, intervals | Centered streaming moments; paths/pairs/scramble means as independent units; explicit absent single-design Sobol inference |
| Convergence/path-count/variance studies | Production multi-replicate RMSE/bias/slope and plain/antithetic/control examples |
| Benchmark/memory/vectorization checks | Measured CPU harness, traced allocations vs buffer sizes, identical output digests and finite scalar/vector tolerances |
| Known distributions and moments | Normal and GBM terminal distribution checks, GBM/Vasicek/Hull–White analytical moments |
| Correlation reproduction | Gaussian integral cross-covariance, unequal OU speeds, OU/log-GBM and single Heston intrinsic loading |
| Research notebooks calling production | Two executed notebooks, eight code cells, one measured RMSE plot; no duplicate model/estimator formulas |
| Optional methods / phase boundary | Latin Hypercube deferred; no GPU/distributed engine, portfolio/netting/collateral/exposure/XVA or financial HTTP job |

## Verification record

The preliminary Windows run passed **644 tests**, explicitly skipped one unconfigured
PostgreSQL test, and achieved **99.06%** branch-inclusive coverage (3,691 statements,
876 branches). It is not live database evidence. Eight later tests add immutable batch
contracts, a bounded antithetic property, typed range failures and injected benchmark
failure/replay checks, including byte-identical synthetic demo execution. The final Docker-backed Windows/Linux suites passed with a real isolated PostgreSQL service.

| Check | Actual result |
|---|---|
| Final Windows Python 3.13.2 + isolated PostgreSQL | **653 passed**, no skips, 62.09 seconds |
| Final Linux Python 3.12.14 production wheel + isolated PostgreSQL | **653 passed**, no skips, 67.38 seconds |
| Final branch-inclusive coverage | **99.15%** on both platforms; 3,702 statements, 880 branches; >=95% passed |
| Ruff/format and strict mypy | All checks passed; 197 source/test/script/Markdown/notebook files formatted; 74 production modules typed |
| Dependency consistency | pip check passed; Linux active 101 exact development pins matched installed versions; notebook/plotting/platform dependencies remain development-only |
| Notebook execution | Both notebooks passed in the project interpreter; 3 + 5 code cells; owned kernel teardown explicitly enabled |
| Documentation | 80 Markdown documents, 11 ADRs, 503 concrete references, local reachability and all four completed-phase ADR review histories passed |
| Packaging | 0.4.0 wheel and sdist built; typed engine, notebooks, docs, helper and metadata contents verified |
| Docker HTTP/database/non-root | health ok, ready/database connected, Parallax Risk / 0.4.0 / phase 4; check-db connected; UID **10001** |
| Scoped cleanup / other projects | Owned API/PostgreSQL containers, default network and disposable volume removed in finally; --rm test container gone; all **35** other container identities/names/projects exactly unchanged |

The existing Starlette/httpx TestClient warning remains on both platforms. The Windows
full run also recorded a pytest cache ACL warning from a reused cache; its results
passed. The helper now chooses a fresh unique project-local cache on every run; a
28-test fresh-cache check passed without that warning. No warning was suppressed.
Notebook kernels
use local Jupyter TCP transport and emitted the library's transport-encryption warning;
this is recorded rather than suppressed. Hosted CI/Python 3.14 were not executed.
No source commit exists in the workspace; source revision is explicitly unavailable.

## Computed synthetic evidence

The demo uses explicit root seed 20251001 and one-year GBM drift .05, volatility .20,
initial spot 100, strike 100. These are synthetic assumptions, not observed prices.
The production expectation is undiscounted; the risk-neutral discounted Gaussian
reference is independently tested against 10.450583572185565.

| Experiment | Observed result |
|---|---|
| Pseudo RMSE log slope, 16 replicate study | -0.5699074100580332 |
| Sobol RMSE log slope, same path counts/replicates | -0.963197916780309 |
| Antithetic estimator variance gain, 8,192 evaluation paths | 1.9809688747358782 |
| Control variance gain, 8,192 evaluation + 2,048 pilot paths | 6.847547022992473 |
| Control work-adjusted gain including pilot paths | 5.478037618393978 |

These seeded results do not establish universal convergence, real-market accuracy
or variance-reduction guarantees. The 32-replicate convergence test uses a broad
pseudo slope range (-.75,-.25), suitable distribution/moment tolerances and a separate
Sobol comparison. Antithetics can worsen variance for an even statistic such as Z².

Measured local GBM harness: 65,536 paths, 32 steps, one state, three repetitions after
warmup. Timing includes generation, immutable buffer publication and SHA256.

| Batch size | Median seconds | Traced peak bytes | Maximum published batch bytes | Full path buffer bytes |
|---|---|---|---|---|
| 512 | 0.8352320000049076 | 584854 | 135168 | 17301504 |
| 4096 | 0.23495949999778531 | 4516406 | 1081344 | 17301504 |

One-step 8,192-path scalar/vector comparison: .059370499999204185 / .0001706000039121136
seconds; observed ratio 348.0099568449572 and maximum absolute difference 0.0.
No timing threshold is a test gate. Tracemalloc is not process RSS, and this local
measurement is not a production capacity promise. Reports are retained under
`artifacts/local/phase4/` with the exact captured environment.

## Decisions and documentation accounting

Eight Markdown documents were created and 46 existing Markdown documents updated.
The two research notebooks are counted separately. All **11 canonical ADRs** have
Phase 4 review rows; IDs 0010 and 0011 are new, and ADR 0004's previous sequence
proposal is now accepted. Six material decision changes: 0001, 0004, 0005, 0008,
0010 and 0011. Previous phase histories and historical reports remain intact.

Fifteen terminology rows explain stream addresses, PCG64DXSM/Ziggurat, Sobol/LMS+shift,
midpoint transforms, antithetic pairs, control pilots, independent units, standard
errors, Student intervals, scramblings, path-count studies, immutable buffers and
traced allocations. Architecture/workflow additions keep mathematical streams and
kernels in domain and injected orchestration in application. No persistence/API
financial workflow was added. Stale sequence/path deferrals were corrected in the
current guides; historical Phase 1–3 evidence was preserved.

Assumptions/limits: caller-declared units/measure/drift; finite binary64; probabilistic
stream separation; pinned-build replay; positive-definite pre-loading correlation;
Gaussian endpoint covariance versus missing integrated-rate discounts; biased Heston
projection; approximate independent-unit intervals excluding model/discretization and
finite-bit quadrature bias; truthful separate pilot/known expectation; retained buffers
or pilot arrays can consume memory; tracing is not RSS. Optional Latin Hypercube,
Brownian bridge/PCA, GPU/distributed execution, portfolio/exposure/XVA/governance and
production capacity documents remain deferred until their authorized phases.

Commands exercised: Ruff/check/format, strict mypy, pytest, pip check, dependency lock
snapshot, all three existing/new demo workflows through integration or direct execution,
new benchmark harness and notebook executor. Pre-commit Ruff/format/mypy passed. Docker checks and cleanup are recorded above;
archives and completed-phase documentation checks pass with the final source metadata.

## Docker retention and cleanup

The verification helper scopes ownership to `parallax-risk-phase4-verification`, uses
an explicitly labelled `--rm` Linux test container and runs the ownership-checked
Phase 4 cleanup in finally. Temporary Linux dev installations and writable files
leave with that test container; only the disposable API/PostgreSQL containers, test
network and disposable test database volume are selected. Useful release/rollback
images, shared base layers/cache, normal Compose data and host reports are retained.
Other projects are never selected. The complete before/after inventory is identical for all 35 other containers.
The useful 0.4.0 image is retained along with 0.3.0/0.2.0/0.1.0 images and shared cache.
Temporary writable test files/development packages left with the --rm test container.
No Parallax verification containers, network or test volume remains.

## File manifest

The phase changes create 36 files and update 59 existing files. These are phase file
changes, not Git commits; the workspace has no source commit. Useful ignored local
reports/dist archives are not source-file changes. The runtime lock was regenerated
without changing its versions and is not counted as an edited file.

| State | File |
|---|---|
| Created | `docs/decisions/0010-independent-sampling-units.md` |
| Created | `docs/decisions/0011-batched-paths-and-gaussian-covariance.md` |
| Created | `docs/methodology/MONTE_CARLO.md` |
| Created | `docs/methodology/MONTE_CARLO_STATISTICS.md` |
| Created | `docs/tutorials/03-FIRST-SIMULATION-RUN.md` |
| Created | `docs/validation/MONTE_CARLO_BENCHMARKS.md` |
| Created | `docs/validation/phase-4.md` |
| Created | `docs/workflows/SIMULATION_WORKFLOW.md` |
| Created | `notebooks/01-monte-carlo-reproducibility.ipynb` |
| Created | `notebooks/02-variance-reduction-convergence.ipynb` |
| Created | `scripts/benchmark_simulation.py` |
| Created | `scripts/demo_simulation.py` |
| Created | `scripts/execute_notebooks.py` |
| Created | `scripts/verify_phase4.ps1` |
| Created | `src/parallax_risk/application/simulation.py` |
| Created | `src/parallax_risk/application/simulation_benchmark.py` |
| Created | `src/parallax_risk/application/simulation_examples.py` |
| Created | `src/parallax_risk/application/simulation_research.py` |
| Created | `src/parallax_risk/domain/simulation/__init__.py` |
| Created | `src/parallax_risk/domain/simulation/analytics.py` |
| Created | `src/parallax_risk/domain/simulation/arrays.py` |
| Created | `src/parallax_risk/domain/simulation/contracts.py` |
| Created | `src/parallax_risk/domain/simulation/controls.py` |
| Created | `src/parallax_risk/domain/simulation/engine.py` |
| Created | `src/parallax_risk/domain/simulation/kernels.py` |
| Created | `src/parallax_risk/domain/simulation/observables.py` |
| Created | `src/parallax_risk/domain/simulation/random.py` |
| Created | `src/parallax_risk/domain/simulation/statistics.py` |
| Created | `tests/fixtures/simulation.py` |
| Created | `tests/integration/test_simulation_workflow.py` |
| Created | `tests/property/test_simulation_invariants.py` |
| Created | `tests/quantitative/test_simulation_convergence.py` |
| Created | `tests/quantitative/test_simulation_paths.py` |
| Created | `tests/unit/test_simulation_contracts.py` |
| Created | `tests/unit/test_simulation_random.py` |
| Created | `tests/unit/test_simulation_statistics.py` |
| Updated | `AGENTS.md` |
| Updated | `CHANGELOG.md` |
| Updated | `CONTRIBUTING.md` |
| Updated | `DEVELOPMENT.md` |
| Updated | `Makefile` |
| Updated | `README.md` |
| Updated | `ROADMAP.md` |
| Updated | `SECURITY.md` |
| Updated | `docker-compose.yml` |
| Updated | `docs/CODEBASE_GUIDE.md` |
| Updated | `docs/DOMAIN_MODEL.md` |
| Updated | `docs/GLOSSARY.md` |
| Updated | `docs/INDEX.md` |
| Updated | `docs/LIMITATIONS.md` |
| Updated | `docs/REPRODUCIBILITY.md` |
| Updated | `docs/WORKFLOW.md` |
| Updated | `docs/api/ENDPOINTS.md` |
| Updated | `docs/api/ERRORS.md` |
| Updated | `docs/api/OVERVIEW.md` |
| Updated | `docs/architecture/COMPONENTS.md` |
| Updated | `docs/architecture/DATA_FLOW.md` |
| Updated | `docs/architecture/DEPENDENCY_RULES.md` |
| Updated | `docs/architecture/OVERVIEW.md` |
| Updated | `docs/architecture/foundation.md` |
| Updated | `docs/decisions/0001-clean-architecture.md` |
| Updated | `docs/decisions/0002-money-representation.md` |
| Updated | `docs/decisions/0003-immutable-market-snapshots.md` |
| Updated | `docs/decisions/0004-random-sequence-reproducibility.md` |
| Updated | `docs/decisions/0005-correlation-validation.md` |
| Updated | `docs/decisions/0006-persistence-boundaries.md` |
| Updated | `docs/decisions/0007-deterministic-curves-and-pricing.md` |
| Updated | `docs/decisions/0008-stochastic-models-and-discretization.md` |
| Updated | `docs/decisions/0009-bounded-calibration-and-uncertainty.md` |
| Updated | `docs/decisions/README.md` |
| Updated | `docs/methodology/CORRELATION.md` |
| Updated | `docs/methodology/GBM.md` |
| Updated | `docs/methodology/INDEX.md` |
| Updated | `docs/methodology/STOCHASTIC_PROCESSES.md` |
| Updated | `docs/methodology/deterministic-pricing.md` |
| Updated | `docs/methodology/primitives.md` |
| Updated | `docs/operations/CONFIGURATION.md` |
| Updated | `docs/operations/DOCKER.md` |
| Updated | `docs/operations/LOCAL_SETUP.md` |
| Updated | `docs/operations/OBSERVABILITY.md` |
| Updated | `docs/operations/RELEASE.md` |
| Updated | `docs/operations/TROUBLESHOOTING.md` |
| Updated | `docs/testing/STRATEGY.md` |
| Updated | `docs/validation/OVERVIEW.md` |
| Updated | `pyproject.toml` |
| Updated | `requirements-dev.lock` |
| Updated | `scripts/check_docs.py` |
| Updated | `src/parallax_risk/__init__.py` |
| Updated | `src/parallax_risk/api/schemas.py` |
| Updated | `src/parallax_risk/application/context.py` |
| Updated | `src/parallax_risk/cli/main.py` |
| Updated | `src/parallax_risk/common/errors.py` |
| Updated | `tests/api/test_operations.py` |
| Updated | `tests/integration/test_database_cli.py` |
| Updated | `scripts/lock_dependencies.py` |

Production image identity: `sha256:4f0d49d5c3f59adbcfefd22ba16d8338a1653facf666c9e89f9fdd7273569738`.
