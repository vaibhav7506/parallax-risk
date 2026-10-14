# Selected risk metric uncertainty

Phase 9 separates three interpretations instead of treating every band as a confidence guarantee.
[Validation](MODEL_VALIDATION.md), [workflow](../workflows/VALIDATION_WORKFLOW.md).

| Method | Inputs and actual work | Interpretation |
|---|---|---|
| Parameter perturbations | Baseline plus caller-supplied cases, all actually revalued with the same model/schema | Linear empirical percentile range of the supplied ensemble; no probability law inferred |
| Independent-unit bootstrap | Retained path/pair/scramble observations, injected resampler and selected scalar statistic | Conditional empirical percentile bootstrap with approximate coverage |
| Calibration propagation | Actual converged fit, available unconstrained covariance and actual local risk revaluations | First-order normal delta-method approximation |

## Bootstrap interface and owned draws

`src/parallax_risk/domain/validation/uncertainty.py` defines IndependentObservations,
BootstrapResampler, IidUnitResampler and UncertaintyBand. Observations must identify
independent units, total paths and source hash. Raw dependent Sobol points reject.
Antithetic observations are pair averages. Independence of caller-supplied scramble
means remains the caller's obligation. Bootstrap resamples units, not individual
members of dependent pairs. Each replicate has a SeedSequence address
(seed,stream,substream,replicate) and an owned PCG64DXSM generator. Evaluation order
cannot consume another replicate's stream. There is no global RNG.

The statistic is actually evaluated on every sample. Wrong sample size or nonfinite
resampler/statistic results reject. Before sampling, replicates*unit_count must fit
the explicit maximum_draws budget. Original statistic, actual replicate statistics,
confidence, linear empirical percentile endpoints, method and evidence hash are retained.
The resampler port permits alternate declared schemes; no unimplemented bootstrap
adapter is silently substituted. User-owned statistic_name describes the supplied
callback, whose correctness/independence cannot be established from a string label.
Percentile intervals may be biased or degenerate and need not contain the original
statistic. They exclude model misspecification, time-grid bias and market-data uncertainty.
See the [official SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
for statistical interpretation; this implementation uses its own owned-unit resampling.

## Calibration uncertainty propagation

FlatHazardProbabilityProblem calibrates one flat hazard from supplied cumulative
probabilities p(t)=1-exp(-h*t) with explicit residual scales and source. The demo
uses labelled synthetic probabilities with deterministic perturbations, never history.
The existing injected SciPy bounded solver produces an actual CalibrationResult.
This does not introduce a CDS bootstrap, market feed or sovereign/default forecast.

calibration_band requires convergence and available covariance with no active bounds.
Parameters retain fitted order and declared units. Actual +/-h and +/-h/2 revaluations
must stay inside optimizer bounds, resolve input changes, retain model identity and
pass derivative consistency at absolute 1e-8 plus relative 1e-3 in derivative units.
Unavailable, constrained or inconsistent uncertainty rejects rather than being invented.
For gradient g and covariance C, propagated variance is g' C g, including cross terms.
Covariance must be finite, square, exactly symmetric and PSD; no clipping, diagonal
replacement or eigenvalue repair. Normal half-width is z_(1-alpha/2)*sqrt(variance).
The [NIST propagation law](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty)
describes the first-order covariance calculation.

The existing covariance assumes local unconstrained iid scaled calibration residuals.
It is not a full market parameter law. Nonlinearities, boundaries, identification,
kinks and default-grid transitions can invalidate normal/linear approximations.
Bands preserve currency and units, source evidence and assumptions; they imply neither
model approval nor guaranteed frequentist coverage. Numerical failures are explicit.

Phase 9 constructs the existing full-rank SVD covariance estimator from weighted
Gram entries, evaluating each symmetric entry once. The lab still rejects asymmetric
caller covariance exactly and never clips eigenvalues. This resolves the observed
Linux BLAS rounding asymmetry at the estimator source. The existing calibration
mathematical assumptions remain unchanged. [Phase 9 evidence](../validation/phase-9.md).
