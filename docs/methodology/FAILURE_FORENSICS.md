# Material-change diagnostics and failure forensics

Phase 10 retains actual before/after, repeated and ordered counterfactual valuations.
The report is machine-readable evidence of **possible causes**, not a causal model,
financial approval or persisted incident workflow.

`src/parallax_risk/domain/validation/forensics.py` owns immutable context, seven cause
kinds, steps and report. `src/parallax_risk/application/validation_forensics.py` owns
injected evaluations. DiagnosticState pairs a real case with six content fingerprints:
market, portfolio, calibration, parameters, numerics and collateral. Adapter name
and model version come from actual outputs. The selected metric/unit schema must
match all endpoints and counterfactuals. Output case hashes must match evaluated inputs.

For change delta = after-before, materiality uses abs(delta) <= absolute + relative
*abs(before). A failed materiality check means a material change worth investigation;
it does not itself mean the model is invalid. Actual before/after repeats are each
checked against their first valuation with a separate repeatability tolerance. A
failed repeat flags numerical instability even when numerical configuration hashes
are unchanged. Passing repeats do not establish accuracy or convergence.

The seven cause buckets are market movement, portfolio movement, calibration
movement, model version, parameter drift, numerical instability and collateral change.
Changed fingerprints identify available evidence, not measured causal contributions.
Numerical configuration changes need separate path/grid/bump convergence studies.
The XVA context helper hashes actual experiment inputs; a caller supplies a retained
calibration hash or a hash explicitly declaring its absence. It cannot authenticate
that calibration provenance. Some groups overlap: CSA changes can also change the
portfolio hash; request-bound market hashes can also move with numerical settings.

Caller-labelled counterfactual cases are evaluated in supplied order. Each bridge
step is output(step)-output(previous). The unexplained residual is endpoint delta
minus the compensated sum of step changes. All full outputs/context fingerprints
are retained. An empty bridge leaves the whole delta as residual; a final endpoint
step reconciles arithmetically. This is not Shapley attribution, a causal partition or
an assertion that one changed fingerprint explains a risk movement. Model-version
changes can be observed across cases, but actually comparing implementations requires
an injected adapter that evaluates those versions; changing a label is not a model run.

The budget is four endpoint/repeat evaluations plus the supplied steps. Retain the
actual input cases, exact model implementations, provenance, ordered states, units,
tolerances and reproduction command. Hashes alone cannot reconstruct inputs. The
synthetic example leaves a portfolio-exposure movement outside its rate/recovery
bridge, so the residual remains visible. Tests also exercise a genuinely changing
synthetic repeat evaluator rather than fabricating an instability flag.

[Workflow](../workflows/ADVERSARIAL_WORKFLOW.md), [verification](../validation/phase-10.md).
