# Model validation lab

Phase 9 adds an in-memory research lab, not institutional approval or a persisted governance workflow.
[Workflow](../workflows/VALIDATION_WORKFLOW.md), [uncertainty](MODEL_UNCERTAINTY.md),
[stress](STRESS_SCENARIOS.md), [evidence](../validation/phase-9.md).

## Comparable models and findings

`src/parallax_risk/application/validation.py` exposes separate ProductionModel and
ChallengerModel protocols and an injected ValidationLab. Both evaluate the exact same
immutable case. Outputs must match its SHA-256 and ordered metric names, exact unit
labels and contribution names. A unit mismatch, stale evidence or unsupported case
rejects; neither conversion nor schema repair occurs implicitly.

ModelOutput retains case hash, model name/version, metrics, result evidence hash and
assumptions. Metric values are finite binary64, distinct from exact Decimal Money.
Comparison is challenger minus production. Each component difference is explicit;
metric difference minus summed component differences remains an unexplained residual.
This arithmetic bridge is not a causal decomposition or a Shapley allocation.

Tolerance is absolute metric units plus a relative fraction of the declared reference
magnitude: abs(error) <= absolute + relative*abs(reference). Equality at the bound passes.
Comparison uses the challenger as reference. Failed checks create immutable open Finding
values containing severity, evidence, affected metric, reproduction instructions, model
version and status. Resolved is an evidence status only; no approval, identity, storage,
authorization or monitoring service is implemented. Successful checks have no finding.

## Independent credit benchmark

CvaBenchmarkCase supplies ACT/365F year fractions from zero, nonnegative linear EE in
one currency, constant annual hazard h>=0, continuously compounded annual rate r and
recovery R in [0,1]. Independent credit and deterministic discounting are assumptions.
The signed CVA is -(1-R)*integral EE(t)*h*exp(-(r+h)*t) dt.

ProductionCvaModel invokes the existing production credit_integral: endpoint-average
D*EE multiplied by exact interval default masses. IndependentCvaBenchmark uses the
constant-EE analytical integral -(1-R)*EE*h*(1-exp(-(r+h)*T))/(r+h), with the T limit at
r+h=0 and expm1 to avoid cancellation. Nonconstant linear EE uses independent SciPy
adaptive quad on each segment, epsabs=epsrel=1e-11, rejecting reported error above
1e-10*max(1,abs(integral)). These methods can differ because production quadrature is
an approximation. A finding is evidence of a discrepancy under a chosen tolerance,
not automatically a coding defect. Core NumPy/SciPy dependencies already exist;
QuantLib/ORE are optional future adapters, not required or claimed as verified.

## Automatic invariants and sensitivities

cva_invariants executes actual production calculations for zero hazard, full recovery,
zero exposure, positive linear scaling and fixed reusable cash collateral offsets.
The collateral check subtracts a supplied nonnegative cash amount from EE with the
mathematically defined positive-part exposure; it does not repair invalid input.
It tests a fixed-offset idealization, not every dynamic CSA, haircut or legal arrangement.
Increasing collateral moves signed CVA toward zero under these assumptions.

Generic equality and monotonicity checks require justified metric schemas/directions.
Exposure is not assumed monotone in time. Sensitivity validation performs five actual
valuations at 0,+/-h,+/-h/2, records central derivatives and checks their consistency,
optionally against an independent target. All moves must be admissible; no one-sided
fallback or correlation repair. Derivative units are metric units per declared factor unit.
Production XVA bumps reuse the existing seven-factor revaluation workflow and streams.

## Finite convergence studies

ProductionXvaModel supplies independent path-unit observations for EPE and independent
credit CVA by actually simulating/repricing portfolios. CVA observation means reconcile
to production CVA because the deterministic credit integral is linear in path exposure.
Dependent-default CVA and a single Sobol design reject in this adapter. Adjacent
antithetic paths are averaged before computing variance; pairs are the independent units.
Generic independent-scramble estimates remain supported when supplied explicitly.

A path ladder increases actual path counts; a step ladder decreases maximum ACT/365F
year-fraction step at fixed path count. Economic inputs, horizon and owned sequence
configuration remain fixed. Caller supplies complete date-aligned scenarios and IM
profiles for each grid; the synthetic helper refines only constant external IM.
Grid changes alter normal-to-path mappings; no nested Brownian coupling is claimed.

Each point retains actual mean, variance, standard error, independent units, total
paths, Student-t approximate confidence bounds and input hash. Estimate counts, SEM
and declared t bounds are validated, without projection. Adjacent mean differences
must meet the explicit stability tolerance and final confidence half-width must meet
the precision tolerance. All adjacent checks plus final precision must pass. This is
finite-study stability, not a proof of convergence, an error bound on time-grid bias,
a confidence interval for an uncomputed paired difference, or market-model accuracy.
[Existing independent-unit statistics](MONTE_CARLO_STATISTICS.md) are reused. The
[official SciPy t reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html)
documents the distribution used in the interval calculation.

## Change and verification locations

Pure validation values/calculations are under `src/parallax_risk/domain/validation/`.
Application adapters and workflows are `src/parallax_risk/application/validation.py` and the adjacent validation adapters.
Independent analytical, grid-bias and statistical checks are
`tests/quantitative/test_validation_lab.py`; actual XVA/stress/calibration/replay checks
are `tests/integration/test_validation_workflow.py`; rejection evidence is
`tests/unit/test_validation_guards.py`. [ADR 0023](../decisions/0023-validation-comparability.md)
and [ADR 0024](../decisions/0024-validation-inference.md) record the policies.

## Phase 10 applicability

Phase 10 extends actual checks into isolated fault detection, same-case bounded search and material-change diagnostics. Only newly failed baseline-passing checks detect faults; repeatability/materiality have separate interpretations.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).
