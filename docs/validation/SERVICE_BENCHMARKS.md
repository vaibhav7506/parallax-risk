# Service performance evidence and method

Phase 12. Measurements are local synthetic workload observations, not portable
throughput or accuracy guarantees. `scripts/benchmark_service.py` runs actual pricing/XVA,
profiling, Python allocation tracing, a 512-trade portfolio and four identical independent
XVA jobs in serial, two threads and two processes including startup. Exact financial
result hashes must agree across all execution modes. Source/OS/runtime and input scope
are retained in artifacts/local/phase12/benchmark-service.json and profile-service.txt.

The 365-movement original collateral check reconstructs every historical balance from
scratch. The cumulative replacement preserves sorted Money addition order, validates
schedule/lag/eligibility and every historical end-of-day state, including same-day
settlements, but scans the ledger once. Independent reference tests cover zero/two-day
lag and both one-way directions/two-way agreements and reject the same invalid history.
No decimal precision, haircut, directional rule or financial tolerance was removed.

On Windows Python 3.13.2 the measured original history check took 1.4460573s; cumulative
check took 0.0338760s (42.6868 ratio). Traced peaks were 41,576 and 55,168 bytes, respectively.
The cumulative check used more tracked memory; this is recorded rather than hidden.
The 512-trade deterministic portfolio took 0.8092637s with 2,784,057 tracked peak bytes.
Four 8-path XVA jobs: serial 3.3012057s, two threads 3.6609138s, two processes 5.8950083s.
All produced equal financial hashes. Small-job parallel startup/GIL overhead did not
justify adding a production process/Redis/distributed service. The asynchronous port
permits a later evidence-backed adapter; currently the local worker implementation is
threads. No Numba/JAX/GPU dependency was added.

`scripts/benchmark_simulation.py` separately verifies streaming/batch/vectorization
behavior on 65,536 paths and 32 steps, three timing repetitions. Batch sizes 512/4096
had measured medians 0.7846623/0.1867783s, maximum published buffers 135,168/1,081,344 bytes,
tracked peaks 584,854/4,516,406 bytes and the same full-stream output digest. Collecting
all paths would require 17,301,504 bytes for that buffer alone. This demonstrates the
latency/memory tradeoff; it does not establish a hard process-memory cap. The scalar
step/vectorized comparison and environment metadata remain in benchmark-simulation.json.

Tracemalloc measures tracked allocations rather than full native/RSS memory. Different
CPU load, numerical libraries, hardware, batch policy and sample sizes change timings.
No latency assertion depends on these local seconds. Explicit work/output admission
and existing performance tests validate bounded inputs/batches and financial replay.
[Service contracts](../methodology/SERVICE.md), [phase evidence](phase-12.md).
