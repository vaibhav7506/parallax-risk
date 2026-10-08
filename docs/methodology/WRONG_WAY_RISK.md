# Explicit wrong-way risk research scenarios

Wrong-way risk means dependence between positive exposure and counterparty default.
Phase 6 compares independent, static-rank and dynamic-spread scenarios using the
same market exposure paths. Results are grid EAD/default summaries, not CVA.

## Independent deterministic baseline

Supply PiecewiseHazardCurve and a separately addressed exponential stream. Default
thresholds are independent of market draws. Reuse that stream for scenario comparison.
Baseline and scenario survival are both reported; identical seeds without identical
addresses, algorithms, environment and inputs do not establish replay.

## Static rank stress

Compute each path's trapezoidal positive-exposure average over the full horizon.
Map midranks to normal scores and mix with independent normals using rho in [-1,1].
Assign the existing exponential thresholds in reverse order of those latent scores.
Positive rho associates high exposure with small thresholds/earlier default; rho=0
returns the exact independent threshold array. Preserve every sampled threshold,
so the deterministic curve's entire sampled default-time marginal is preserved.
Ties use average ranks and stable sorting. This is finite-sample rank stress, not an
exact population Gaussian copula calibration. It depends on the full future path
and is explicitly non-adapted; do not interpret it as an executable causal hazard
process or general arbitrage-free pricing model.

## Dynamic correlated market/credit drivers

Bind a positive GBM credit spread within the validated market simulation request.
Its Brownian driver can correlate with rates or FX through the existing explicit
CorrelationMatrix. An injected spread policy produces nonnegative intensity.
Integrate left-endpoint intensity and invert with an independent unit-exponential
threshold. Deterministic baseline and dynamic sample-average survival can differ.
A difference in default-weighted grid exposure combines dependence and changed
marginal default probabilities; the headline ratio alone does not isolate WWR.

The quantitative dynamic test separately permutes complete credit histories across
20,000 actual correlated market paths. This preserves the empirical intensity and
conditional-survival marginal while breaking market/credit pairing. The specified
positive-correlation synthetic example must increase default-weighted exposure by
at least 15%; this is a test of that experiment, not a theorem for all books or rho.
Static tests similarly check preserved thresholds and a selected positive stress.
No universal monotonicity in time, hazard volatility or correlation is asserted.

## Comparison output and limits

Expose baseline/scenario default counts, PD, unconditional mean with nondefaults zero,
conditional mean given default, difference and ratio. A zero baseline mean has no
ratio (None); a no-default conditional mean is None. EAD uses right grid endpoints
of alive collateral paths; default-conditioned margin freeze, MPOR, discounting,
recovery losses, bilateral defaults and stochastic recovery remain absent.
No baseline calibration, stress certification or regulatory compliance is claimed.

Static and dynamic approaches have different calibration/arbitrage limitations; the
research context is discussed by [Vrins, Wrong-Way Risk Models](https://arxiv.org/abs/1605.05100).
The repository implements the above declared policies, not all models from that paper.
[Credit formulas](CREDIT_DEFAULT.md), [exposure limits](EXPOSURE.md),
[workflow](../workflows/EXPOSURE_WORKFLOW.md), [Phase 6 evidence](../validation/phase-6.md).
