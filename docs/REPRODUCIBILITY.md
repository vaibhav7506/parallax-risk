# Reproducing pricing and calibration

Reproduction matters because a reviewer must distinguish changed inputs from a
changed model or environment. Current deterministic pricing needs the same contract,
snapshot, curves, conventions and model version; it does not consume random draws.

| Evidence | Current implementation / limitation |
|---|---|
| RiskRunId, UTC timestamp, uint64 seed | RunContext; inject ID/time for identical metadata; seed is metadata only |
| Configuration hash | Canonical nonsecret Settings digest; credentials excluded, DB presence recorded |
| Market hash | Includes identity/version, observations/conventions and provenance |
| Curve-set hash | Nodes, conventions, IDs and discount/projection assignments |
| Instrument hash | Complete typed contract and supplied schedule |
| Model name/version | deterministic-discounting / 0.2.0 in PricingResult |
| Source revision/runtime/libs | Record externally with the run; locks and phase evidence exist, automatic source/environment capture absent |
| Calibration identity/parameters/data/settings | CalibrationRunId, input/configuration hashes, bounds, fitted parameters, residuals/status and enclosing RunContext |
| Portfolio hash/sequence algorithm | NOT IMPLEMENTED; later phases |

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
