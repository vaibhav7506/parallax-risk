# Monte Carlo benchmark methodology

`python scripts/benchmark_simulation.py` measures the production engine on 65,536
synthetic GBM paths, 32 time steps, one state, batch sizes 512 and 4,096, with three
repetitions after a complete workload warmup. Each iteration starts a fresh owned
stream. The workload includes generation, immutable publication and SHA-256 hashing.
Repetitions must produce identical complete buffer digests.

Report actual times, median, paths/second, request/environment hashes, maximum
published batch bytes, equivalent full path buffer bytes and `tracemalloc` peak.
Tracing reports tracked Python/NumPy allocations; it is **not process RSS** and
does not guarantee all native library allocations are tracked. Path publication
copies working data to immutable bytes; inputs, shocks, working states, covariance
loadings and a suspended generator contribute additional memory.

The batch buffer grows with batch size, grid length and state dimension. A caller
that retains every batch uses memory proportional to total paths. Pilot control
regression also retains its pilot observation vectors; it is not a fully streaming
multivariate regression. There is no configured hard RSS limit.

The vectorization benchmark applies the same supplied shocks to the production
scalar strategy and vectorized kernel for 8,192 one-step transitions. It checks
`atol=rtol=1e-12`, then reports both observed times and their ratio. No test fails
solely because a timing ratio is small. Timings depend on host load, CPU/build and
tracing; one local result is not a deployment throughput guarantee.

Actual measured values and environment are recorded after execution in
[Phase 4](phase-4.md). Preserve JSON under `artifacts/local/phase4/`; useful reports
remain after scoped Docker cleanup. GPU/distributed execution, Brownian bridge/PCA,
stress scaling and a production capacity SLO are deferred.

Production: `src/parallax_risk/application/simulation_benchmark.py`.
Tests: `tests/integration/test_simulation_workflow.py`.
See [paths](../methodology/MONTE_CARLO.md),
[ADR 0011](../decisions/0011-batched-paths-and-gaussian-covariance.md).
