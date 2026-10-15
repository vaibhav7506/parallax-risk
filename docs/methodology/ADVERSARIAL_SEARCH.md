# Bounded adversarial model search

The Phase 10 objective is absolute production/challenger disagreement for a selected
metric, in its exact declared unit. Both adapters must evaluate the **same actual
case** and retain input hashes. Model identities and metric/unit schemas stay fixed
throughout the search. No disagreement is labelled market likelihood or accuracy.

`src/parallax_risk/domain/validation/search.py` owns SearchDimension, linear
restrictions, SearchSpec, optimizer status and every paired valuation.
`src/parallax_risk/application/validation_search.py` validates feasibility and enforces
an actual evaluation budget. The injected SearchOptimizer port is implemented by
`src/parallax_risk/infrastructure/validation/scipy_search.py` using SciPy differential
evolution, an owned StreamKey PCG64DXSM generator, Latin-hypercube initialization,
one worker, immediate updates and no polishing. Imports do not start optimization.

Every bound has name, exact unit, finite lower < upper and rationale. Linear
restrictions require aligned finite weights and lower <= sum(weights*parameters)
<= upper. A source label declares why the ranges were chosen; it is not authenticated
market data. Complete case constructors additionally enforce economic admissibility.
An invalid candidate or model evaluation raises explicitly, without clipping,
correlation repair, substituted penalty or failed-result fallback. The adapter
preserves callback validation errors that SciPy otherwise wraps as map-shape errors.
An empty feasible population returns an error and no risk conclusion.

The planned maximum paired evaluations is (iterations+1)*max(5,population_multiplier
*dimension_count), with all bounds strictly nondegenerate and no polishing. The
application also enforces the actual budget. One paired evaluation calls both models,
so its maximum model-call count is twice the paired budget. Optimizer status, message,
iterations, actual count, implementation/version, key and every feasible candidate
are retained. The reported best must match the maximum actual retained discrepancy;
it is not revalued outside the budget. Budget exhaustion can leave convergence false.
Convergence is a population stopping criterion, not a proven global maximum.

## CVA models and six-factor XVA mapping

The cheap synthetic demo compares actual ProductionCvaModel endpoint integration
against the Phase 9 independent flat-hazard analytical/adaptive benchmark, over rate,
hazard and recovery levels. Its declared combined rate+hazard restriction is explicit.
These intervals are synthetic research assumptions, not historical plausible ranges.

`src/parallax_risk/application/validation_search_models.py` also supplies a CVA-only
actual XVA adapter, an independent-credit continuous quadrature challenger and
XvaSearchCases. The challenger reruns production exposure, then independently
integrates D(t)*linear-EE(t)*S(t)*h(t)*(1-R), splitting exposure, discount and hazard
knots. It retains signed negative CVA and rejects quadrature error above
1e-9*max(1,abs(segment_loss)), with SciPy epsabs/epsrel=1e-10. It rejects static/dynamic
WWR. Shared simulation/pricing/exposure errors are **not independently challenged**.

XvaSearchCases applies ordered absolute **deltas from a fixed baseline** using actual
XvaRevaluation.bump. Supported coordinates are annual decimal rates, declared model
volatility, Brownian correlation, annual decimal credit-triangle spreads, recovery
fractions and CSA receive thresholds in agreement currency. The dimension labels
must match factor_unit exactly. Spread-before-recovery and recovery-before-spread
can differ; retain factor order. The daily zero-haircut CSA and initial-account
requirements remain. Full matrix PSD/Cholesky, valid recovery/volatility/hazard and
other Phase 7 restrictions still apply. Funding, supplied IM and origin fixings
remain fixed according to that workflow. A four-path synthetic integration test
exercises all six kinds; it is not precision or real-market validation evidence.

There is no unconstrained finance optimizer, automatic nonlinear PSD projection,
out-of-sample selection correction, historical feed, global-optimality proof or
adversarial event probability. Bounds may fail to include economically important
states. Shared fixed streams improve repeatability but do not remove sampling/grid
bias or selection effects.

The API choices were checked against the primary [SciPy differential evolution
reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html).
[Workflow](../workflows/ADVERSARIAL_WORKFLOW.md), [verification](../validation/phase-10.md).
