# Reproducing pricing, calibration and simulation

Reproduction matters because a reviewer must distinguish changed inputs from a
changed model or environment. Current deterministic pricing needs the same contract,
snapshot, curves, conventions and model version; it does not consume random draws.

| Evidence | Current implementation / limitation |
|---|---|
| RiskRunId, UTC timestamp, uint64 seed | RunContext; inject ID/time for identical metadata; seed is metadata for pricing/calibration and initializes explicit simulation streams |
| Configuration hash | Canonical nonsecret Settings digest; credentials excluded, DB presence recorded |
| Market hash | Includes identity/version, observations/conventions and provenance |
| Curve-set hash | Nodes, conventions, IDs and discount/projection assignments |
| Instrument hash | Complete typed contract and supplied schedule |
| Model name/version | deterministic-discounting / 0.2.0 in PricingResult |
| Source revision/runtime/libs | Simulation captures Python/NumPy/SciPy/platform plus optional supplied source revision; other workflows preserve external evidence |
| Calibration identity/parameters/data/settings | CalibrationRunId, input/configuration hashes, bounds, fitted parameters, residuals/status and enclosing RunContext |
| Sequence algorithm/order | StreamKey, PCG64DXSM Ziggurat or complete scrambled Sobol midpoint design, explicit layout and request hash |
| Portfolio hash/persisted lineage | NOT IMPLEMENTED; later phases |

## Reproduce a run

1. Install the locked environment using [development setup](../DEVELOPMENT.md).
2. Preserve `data/sample/phase2_market.json` and the release/source state; every
   sample observation is synthetic, not vendor data.
3. Run `python scripts/demo_deterministic.py` twice. Compare stdout JSON; log
   timestamps on stderr are operational and intentionally vary.
4. Inspect snapshot/curve hashes, contract/model metadata and cash-flow contributions.
   The demo injects a fixed run ID, 2025-01-01 UTC time and seed 0.
5. For a custom library run, explicitly supply the same typed snapshot/curves/contract,
   payment policy and sensitivity bump; inject RunContext ID/time/seed.

`tests/integration/test_deterministic_workflow.py` checks byte-identical demo stdout.
`tests/quantitative/test_deterministic_pricing.py` checks price/evidence consistency.
New CLI `run-context` calls produce fresh IDs/current time, so separate invocations
do not promise identical envelopes. A matching seed alone promises no stochastic
sequence equality; see [ADR 0004](decisions/0004-random-sequence-reproducibility.md).

Record `git rev-parse HEAD` where a commit exists, `python --version`, dependency
locks and image identity with future saved evidence. The initial workspace had no
commit; never invent one. Cross-platform exact bitwise equality for arbitrary
numerics is not asserted by the current finite-tolerance tests.

## Reproduce calibration

Preserve `data/sample/phase3_calibration.json`, model 0.3.0, numerical settings/bounds
and the locked SciPy/NumPy environment. Run `python scripts/demo_calibration.py`.
The example injects fixed IDs, time and seed; seed is unused by these deterministic
objectives. Tests repeat actual fits in the same environment and compare full results.
Cross-platform fits are validated with finite tolerances, not bitwise identity. Log
timestamps vary. Keep convergence, residuals and uncertainty evidence; matching hashes
are content identity, not proof of trustworthy observations or mathematical correctness.

## Reproduce simulation research

Run `python scripts/demo_simulation.py` twice on the pinned source/environment;
stdout JSON is identical. Synthetic examples inject an explicit environment-independent
RunContext configuration. Metadata includes request/observable hashes, model/scheme,
grid, units/measure, root seed, stream/substream, transform/layout and environment.
Request hash includes batch size; paths are verified unchanged under different batch
sizes on the pinned builds, while reductions may differ in final rounding.

Run `python scripts/execute_notebooks.py` in the locked project interpreter to verify
both research notebooks. Outputs are saved only after successful execution and owned
kernels are shut down. Notebook execution timestamps and benchmark wall times are
observations, not deterministic outputs. Runtime connection files remain local/ignored.
There is no source commit in this workspace; source revision is explicitly None.
Do not infer bitwise compatibility across CPU/library/build changes.
See [sequence policy](methodology/MONTE_CARLO.md) and
[statistical units](methodology/MONTE_CARLO_STATISTICS.md).
