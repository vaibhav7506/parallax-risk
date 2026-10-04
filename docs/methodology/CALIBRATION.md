# Bounded instrument calibration

## Intuition

Calibration finds parameters whose model prices fit a set of observations. An
optimizer can stop successfully even when fit is poor, parameters are constrained,
or several parameter sets fit equally well. Parallax Risk preserves those distinctions.

## Objective, units and provenance

For observations y_i, model predictions p_i and strictly positive user scales s_i,
residuals are `r_i=p_i-y_i`, and scaled residuals `f_i=r_i/s_i`.
The objective is `0.5 sum(f_i²)` under finite lower/upper parameter bounds.
Raw RMSE is `sqrt(sum(r_i²)/m)` in observation units; scaled RMSE uses f_i.
Scale is a residual divisor, not automatically a bid/ask, confidence interval or
variance estimate. Quote order is preserved. No quote is silently deleted.

All problems specify currency, aware UTC as-of instant, unique quote/instrument
identity, finite year-fraction maturity/expiry and explicit SourceMetadata. Future
observed-at timestamps and model-context arbitrage violations reject data. Calibration
quotes are distinct from snapshot raw volatility observations. Synthetic sample
SourceMetadata.is_sample is true. Source/configuration changes alter content hashes.

| Objective | Fitted parameters | Fixed context | Observation units |
|---|---|---|---|
| VasicekBondProblem | a,theta,sigma | Initial short rate | Unit-nominal discount factors |
| HullWhiteBondOptionProblem | a,sigma | Explicit smooth initial forward curve | Bond-call nominal fractions |
| HestonCallProblem | k,theta,xi,rho,v0 | Spot, continuous r/q, FourierSettings | Currency units per underlying unit |

## Software and optimization

`src/parallax_risk/domain/calibration/contracts.py` defines CalibrationProblem,
ParameterBound, CalibrationSettings, CalibrationResult and ParameterUncertainty.
`src/parallax_risk/domain/calibration/problems.py` maps model parameters to predictions.
The application port/service is `src/parallax_risk/application/calibration.py`;
strict discriminated Pydantic ingestion is
`src/parallax_risk/application/calibration_inputs.py`.
`src/parallax_risk/infrastructure/calibration/scipy_solver.py` implements the injected
solver using [SciPy bounded least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).

Chosen options are TRF, linear loss, three-point finite-difference Jacobian and
Jacobian scaling. Defaults: max_nfev=1000; ftol/xtol/gtol=1e-10. Tolerances require
[1e-14,1). Bounds are finite, lower<upper and initial inclusive inside; names/order
must match the objective. Model-domain extremes are evaluated before optimization;
SciPy TRF may move a boundary starting guess slightly into the feasible interior;
the original declared starting values remain recorded in parameter_bounds.
errors propagate as CalibrationError with the original authored error as cause.
Numerical differentiation is bounded by SciPy; no complex-step assumption is used.

The result reports CalibrationRunId, model name/version, input-data hash, configuration
hash, bounds/initial values, fitted named parameters, predictions, signed/raw/scaled
residuals, both RMSEs, maximum residual, optimizer status/message/optimality,
active bounds and evaluation counts. `optimizer_evaluations` is SciPy nfev;
`objective_evaluations` includes numerical-Jacobian calls but excludes preflight and
final repricing. An exhausted budget returns status FAILED; `require_converged()`
raises explicitly if a caller requires success. Evaluation failure raises an exception
instead of replacing the objective with an arbitrary penalty.

## Uncertainty and identification

An SVD of the scaled Jacobian uses rank threshold `eps*max(m,n)*largest_singular`.
When converged, full-rank, interior, m>n and condition number<=1e10, covariance is
`[sum(f_i²)/(m-n)] (J^T J)^-1`, evaluated by SVD. Standard errors are square roots
of its diagonal. The result always exposes rank, residual degrees of freedom and
condition number where defined. Otherwise covariance/errors are absent, with a
reason: failure, active bounds, rank deficiency, no degrees of freedom or ill conditioning.
No pseudoinverse or jitter disguises uncertainty for unidentified parameters.

This is a local linear iid-scaled-residual approximation, not posterior uncertainty,
robust quote-error inference or a confidence guarantee. Nearly zero errors on generated
exact data do not imply market certainty. Optimizer convergence is not a fit-quality
approval or a global minimum claim. Feller is not imposed as a Heston constraint.

## Example, validation and limitations

`data/sample/phase3_calibration.json` contains three generated instrument datasets,
known generating parameters, provenance, initial values and bounds. Run
`python scripts/demo_calibration.py`; stdout contains computed JSON, stderr safe
workflow logs. [Tutorial](../tutorials/02-FIRST-CALIBRATION-RUN.md) explains the outputs.

`tests/quantitative/test_calibration.py` tests parameter recovery/replay, initialization
and perturbation stability, weighted/raw metrics, bounds, weak identification and
budget failure. `tests/unit/test_calibration_guards.py` rejects malformed bounds,
sources, data and boundary payloads. `tests/integration/test_calibration_workflow.py`
executes the real service/example. No global search, historical estimation, multistart,
bootstrap, calibration uncertainty propagation, persisted calibration runs or financial
HTTP/CLI workflow is implemented. These limits are visible in [limitations](../LIMITATIONS.md).
