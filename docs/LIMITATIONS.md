# Current limitations

These limitations apply to implemented Phases 1–4. Preserve them until an actual
change and evidence justify revision; record revisions in the decision history.

| Category / limitation | Impact and affected code | Mitigation / phase |
|---|---|---|
| Binary64 valuation, no settlement rounding | Finite precision and cancellation; pricing/_numbers and sensitivities | Explicit tolerances, independent formulas and bump studies; rounding policy absent |
| Ten-code currency subset, supplied holidays/day counts | Not a complete market convention/calendar feed; common | Supply supported explicit conventions; expand with verified requirements |
| Daily snapshot cutoff, synthetic demo data | No intraday/freshness/vendor/authenticity guarantee; domain/market | Label provenance/sample status, validate dates; integrations deferred |
| Deposit/par-swap single-curve bootstrap | No heterogeneous basis/spot lag/convexity calibration; curves/bootstrap | Use supported conventions; stochastic model calibration is separate |
| Default-free dirty bond PV; simple swap coupons | No credit/default/optionality/clean-price/ex-coupon/compounded index | Use only supported explicit contracts; no invented adjustments |
| Direct FX / no basis | No inverse/cross synthesis or arbitrary portfolio conversion | Supply exact direct pair/settlement and supported funding assumption |
| Zero-knot risk, explicit finite bumps | Not market-quote DV01; truncation/cancellation depends on h | State scope/signs, test meaningful bump stability |
| No portfolio/exposure/XVA/capital | Research paths/statistics cannot calculate counterparty default losses | Phases 5–8 planned |
| No validation lab/mutation/governance persistence | Current tests are not independent institutional approval or model inventory | Phases 9–11 planned |
| Operational API only, unauthenticated local service | No production risk jobs, authorization, scale/HA or security certification | Loopback/development use; Phase 12 planned |
| Incomplete automatic lineage | Simulation captures sequences/runtime/platform and optional supplied source revision; portfolio/persisted lineage absent | Preserve external source/runtime evidence; phased lineage work |
| Exact version locks without hashes; release-tag bases | Whole-environment rebuild immutability not guaranteed | Record actual versions/image IDs and revalidate updates |
| Python 3.14 unverified; hosted CI not observed | Metadata support is broader than local evidence | Report tested 3.13.2/3.12.14; execute matrix when hosted CI runs |

No regulatory compliance, model accuracy, performance or external-pricer benchmark
certification is claimed. Existing adapter deprecation warnings remain in
[Phase 2 evidence](validation/phase-2.md). See [security](../SECURITY.md) and
[methodology](methodology/INDEX.md) for precise assumptions and failure domains.

Phase 3 adds constant-parameter Gaussian rates, caller-drift GBM and Q Heston.
Hull–White accepts only explicit linear smooth forwards; exact rate steps omit joint
stochastic integrated discounts. Heston projected Euler is biased at the boundary,
not exact/full-truncation; European calls assume constant continuous r/q, with estimated
quadrature errors. Calibration is local, bounded, synthetic in demos, without market
validation/global search/bootstrap/persistence. Covariance is a local iid-scaled-residual
estimate, absent for constrained or unidentified fits. Correlation repair changes
assumptions, requires explicit opt-in and is not a nearest-matrix optimizer.
See [models](methodology/STOCHASTIC_PROCESSES.md), [Heston](methodology/HESTON.md)
and [calibration](methodology/CALIBRATION.md).

Phase 4 is CPU research: no Latin Hypercube, Brownian bridge/PCA, GPU/distributed
execution, generic user-process vectorization or singular-correlation factor fallback.
QMC requires complete powers of two and has an explicit finite-bit midpoint normal
convention with quadrature bias. Student t intervals are approximate and exclude
model, calibration and discretization bias. Control expectations are caller assumptions;
separate addresses cannot detect mislabelled pilot reuse. Heston remains projected
Euler, and exact rates omit joint integrated discounts. Collecting every batch loses
streaming memory savings; traced allocations are not RSS or a hard memory budget.
See [paths](methodology/MONTE_CARLO.md), [statistics](methodology/MONTE_CARLO_STATISTICS.md)
and [benchmarks](validation/MONTE_CARLO_BENCHMARKS.md).
