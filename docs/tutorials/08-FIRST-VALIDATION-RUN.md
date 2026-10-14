# First model validation run

Install the project/development environment from [local setup](../operations/LOCAL_SETUP.md).
From the repository root run `python scripts/demo_validation.py`.
The result is labelled Parallax Risk, release 0.9.0, is_synthetic=true and model_approval=false.

Inspect comparison.differences: challenger minus production uses a strict stated
currency tolerance. Independent analytical CVA and production quadrature can differ
at a finite grid. Inspect findings and evidence before deciding whether the difference
is a numerical approximation, an inappropriate assumption or a software defect.

Inspect invariants, local_fx, paths and time_steps. A failed convergence threshold
remains a failed result; small synthetic path counts need not meet precision criteria.
Inspect bootstrap_cva, parameter_cva and calibration_cva separately: conditional
bootstrap coverage, supplied-ensemble range and local normal propagation have different
interpretations. Inspect stresses for actual hypothetical/combined revaluation and
ordered shock provenance. The demo contains no observed historical market series.

The input case hashes, result evidence, assumptions, independent units, actual draws,
model versions and reproduction instructions are retained in the JSON. Save the result
outside disposable container writable layers if you need it later. Replay is exact
within the verified runtime; cross-platform bit identity is not claimed.

To change a tolerance or scenario, compose typed library inputs following the
[workflow](../workflows/VALIDATION_WORKFLOW.md) and [method](../methodology/MODEL_VALIDATION.md).
There is no financial HTTP endpoint or model approval button. Phase 10 remains deferred.
