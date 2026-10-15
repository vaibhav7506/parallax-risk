# Controlled quantitative mutation testing

Phase 10 implements immutable mutation declarations, injected operation replacements
and baseline-qualified detection evidence. This is a research diagnostic, not a
certified defect-detection rate for all Parallax Risk models.

`src/parallax_risk/domain/validation/mutation.py` owns the 15 fault kinds and reports;
`src/parallax_risk/application/validation_mutation.py` runs the supplied model and
validation suite. It evaluates the fault-free baseline first, then one isolated
fault per evaluation. Nothing patches global functions or enables production faults.

A detection requires a check that **passes on the baseline and fails on that mutant**.
An already failing baseline check cannot kill a mutant. Every executed mutant retains
its output, checks, new failed IDs and detected/missed status. Category and aggregate
rates equal newly detected / executed mutations. Equivalent or unexercised faults
remain misses in the denominator. Execution errors abort explicitly; they do not
become manufactured detections. The runner requires matching ordered check/metric
schemas and unchanged per-check acceptance bounds, finite discrepancies, consistent pass/finding states and actual input hashes.
The budget includes the baseline and all mutant evaluations.

## Implemented operation seams

`src/parallax_risk/application/validation_probes.py` supplies a labelled synthetic
ProbeCase and OperationProbeModel. These are operation-seam probes, not AST/source
mutation of every production engine. The injected MutationModel protocol also allows
caller-supplied complete model adapters. Retain the actual input case, mutations,
selected suite, targets, units, tolerances and reproduction command alongside reports.

| Fault | Explicit controlled replacement | Fault-free operation / independent target |
|---|---|---|
| Discount factor | Reverse continuous-discount exponent | exp(-rT), annual decimal r, years T |
| Sign convention | Reverse signed unilateral CVA | Actual production credit integral; hand endpoint/default-mass target |
| Recovery | Use R as LGD | Production RecoveryAssumption complement 1-R |
| FX conversion | Divide instead of multiply declared direct FX | 100 base units times quote/base FX; no cross-pair inference |
| Day count | ACT/360 instead of ACT/365F | Production year_fraction; civil-day difference / 365 |
| Correlation sign | Reverse rho before validated Cholesky | Reconstructed covariance; independently supplied rho |
| Missing collateral | Omit held cash | Actual restricted CCR unmargin replacement cost max(V-C,0) |
| Incorrect threshold | Omit receive threshold | Actual receive-only CSA VM target max(V-TH,0) |
| Exposure date | Select prior grid node | Actual right-endpoint exposure_at_default at last interval midpoint |
| Look-ahead calibration | Select future supplied dated fit | Latest supplied fit available at as_of; timing selection only |
| Volatility scaling | Multiply decimal volatility by 100 | Actual GBM diffusion at spot 100; 100 sigma units/year^0.5 |
| Path count | Keep first two supplied IID units | Actual OnlineMoments SEM; independent sample-variance formula |
| Interpolation | Linear instead of log-linear | Actual positive-ordinate midpoint, sqrt(1 times .81)=.9 |
| Ignored MPOR | Zero maturity factor | Actual restricted margined CCR contribution, 1.5 sqrt(MPOR/250) |
| Default probability | Cumulative rather than interval PD | Actual PiecewiseHazardCurve interval mass S(a)(1-exp(-h(b-a))) |

Cash/threshold probes assume one currency and ideal settled cash; business-day MPOR
is distinct from calendar-day CSA closeout. The look-ahead probe does not refit models
or establish a full temporal calibration-validation pipeline. The insufficient-path
probe challenges sampling diagnostics, not every exposure simulation setting. The
full engine's omitted default-conditioned MPOR is still a limitation; zeroing a CCR
maturity factor does not implement that missing closeout model.

The example uses hand-specified synthetic data, binary64 calculations and absolute
1e-10 plus relative 1e-12 tolerances in each metric's declared units. The deliberately
weak sign-only suite demonstrates retained misses. Zero rate/rho/cash/threshold/vol,
FX=1, R=.5 and fully available dated observations can make some faults equivalent;
tests verify those misses without silently removing them.

[Workflow](../workflows/ADVERSARIAL_WORKFLOW.md), [verification](../validation/phase-10.md).
