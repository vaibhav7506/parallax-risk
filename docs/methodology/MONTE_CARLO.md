# Monte Carlo paths and random sequence policy

Phase 4 implements a CPU research engine in `src/parallax_risk/domain/simulation/`.
Configuration is immutable; execution owns its random state and working arrays.
Models and scalar discretization strategies remain independently usable.

## Inputs and layout

`SimulationRequest` contains ordered components, initial states, explicit schemes,
state units, measures, a strictly increasing nonnegative year-fraction `TimeGrid`,
path/batch counts, a `SequenceSpec` and optional ordered `CorrelationMatrix`.
No day count, currency conversion, calibration result or probability measure is
inferred. The caller is responsible for a drift consistent with the declared measure.
Components do not dynamically feed stochastic rates into another component's drift.
Correlation alone does not establish a jointly arbitrage-free tradable market.

Published arrays have shape `(path, time, state)`, include the initial state, and
use binary64. `FrozenArray` copies into immutable little-endian C-order bytes;
its NumPy view cannot be made writable. This publication copy consumes memory.
The iterator generates one batch; collecting all batches deliberately loses the
streaming memory benefit. Input hashes and buffer hashes use different schemas.

## Sequence policy

`StreamKey(seed, stream, substream)` validates a uint64 root seed and uint32 IDs.
An explicit `SeedSequence(seed, spawn_key=(stream, substream))` initializes
`Generator(PCG64DXSM(...))`; addresses do not depend on allocation order.
Distinct addresses give streams with the probabilistic separation described by
[NumPy](https://numpy.org/doc/stable/reference/random/parallel.html), not a proof
of mathematical independence for arbitrary numbers of streams.

Pseudo normals use NumPy's binary64 Ziggurat implementation. Draw order is path,
step, pre-loading driver. Antithetic normals are adjacent complete `Z,-Z` pairs;
path and batch counts must be even. No module creates a global RNG.

Sobol uses SciPy LMS+shift scrambling, explicit RNG and `optimization=None`.
Every complete design contains `2**m` paths, including its initial point, and
batches are powers of two. No skipping, thinning or arbitrary path counts.
The flattened step/driver dimension cannot exceed 21,201. Bits are explicit
(default 30, supported 1–52); counts cannot exceed `2**bits`.
Normals are `ndtri(u + 0.5 * 2**(-bits))`, placing finite-bit points at bin centers.
This explicit quadrature convention avoids infinite endpoint normals without
clipping. It creates finite-bit quadrature bias/truncated tails, which confidence
intervals do not measure. Small bit depths are pedagogical, not accuracy defaults.
See [SciPy's design constraints](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html).
Sobol plus antithetics and optional Latin Hypercube are not implemented.

## Models, dependence and time discretization

Vectorized kernels support exact GBM/Vasicek/Hull–White transitions and explicit
Euler–Maruyama; Heston also supports its reported projected variance/log-spot Euler.
Scalar/vectorized reconciliation uses finite tolerances. Generic Euler rejects
invalid spot/variance proposals; there is no clipping or scheme fallback.
Projection counts count affected model steps, and retain the scheme's bias warning.

The input correlation is between pre-loading **Brownian drivers**, ordered
`component.d0`, `component.d1`, etc. It must be numerically positive definite
under ADR 0005's Cholesky policy. Singular PSD matrices require an explicit future
factor policy and are rejected here. Heston's two pre-loading drivers must have
zero mutual correlation; its model loading applies rho once. Cross-component
entries concern pre-loading drivers, not automatically Heston's final variance driver.

Exact OU innovations integrate exponentially weighted Brownian increments. Applying
the Brownian rho directly to their standardized endpoint innovations would be wrong
for unequal speeds or an OU/GBM combination. For speed `a_i` (`0` for log-GBM or
Euler), each step's normalized covariance is

`C_ij * B(a_i+a_j,dt) / sqrt(B(2*a_i,dt)*B(2*a_j,dt))`, with `B(0,dt)=dt`.

`innovation_correlation` constructs this covariance and validates/factorizes it.
Factor reductions use a fixed order independent of batch shape. Exact Gaussian
joint transitions are exact for the supported constant-coefficient OU/log-GBM
variables; Heston and Euler remain time discretizations. Exact endpoint rates
do not include the joint integrated short rate or stochastic discount factors.

## Provenance and validation

Metadata records request hash, engine version 0.4.0, complete sequence specification,
algorithm/normal transform, draw layout, states/units/measures, times, correlation
hash, Python/NumPy/SciPy/platform and optional caller-supplied source revision.
An unavailable source revision is `None`; no commit is invented. The application
adds RunContext, observable identity/hash/unit, confidence level and control evidence.

Tests verify pinned-environment replay across different batch sizes, normal/GBM
distribution and moments, Vasicek/Hull–White moments, scalar reconciliation,
correlation reproduction and Heston projection behavior. Batch invariance is
tested for installed versions; [NumPy's compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html)
does not guarantee all generator methods across future sizes/builds/environments.
Cross-platform tests use deliberate finite tolerances; broad bitwise compatibility
across CPUs, builds or library changes is not claimed.

See [statistics](MONTE_CARLO_STATISTICS.md), [workflow](../workflows/SIMULATION_WORKFLOW.md),
[ADR 0004](../decisions/0004-random-sequence-reproducibility.md),
[ADR 0011](../decisions/0011-batched-paths-and-gaussian-covariance.md) and
[Phase 4 evidence](../validation/phase-4.md).

Phase 6 [exposure workflow](../workflows/EXPOSURE_WORKFLOW.md) consumes the same
immutable batches for conditional repricing. Credit thresholds use separate addressed
PCG64DXSM streams; no global generator is introduced. Profile statistics report no
IID/QMC confidence intervals. The retained-matrix cap does not bound peak allocations.
