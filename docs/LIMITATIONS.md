# Current limitations

These limitations apply to implemented Phases 1–8. Preserve them until an actual
change and evidence justify revision; record revisions in the decision history.

| Category / limitation | Impact and affected code | Mitigation / phase |
|---|---|---|
| Binary64 valuation, no settlement rounding | Finite precision and cancellation; pricing/_numbers and sensitivities | Explicit tolerances, independent formulas and bump studies; rounding policy absent |
| Ten-code currency subset, supplied holidays/day counts | Not a complete market convention/calendar feed; common | Supply supported explicit conventions; expand with verified requirements |
| Daily snapshot cutoff, synthetic demo data | No intraday/freshness/vendor/authenticity guarantee; domain/market | Label provenance/sample status, validate dates; integrations deferred |
| Deposit/par-swap single-curve bootstrap | No heterogeneous basis/spot lag/convexity calibration; curves/bootstrap | Use supported conventions; stochastic model calibration is separate |
| Default-free dirty bond PV; simple swap coupons | No credit/default/optionality/clean-price/ex-coupon/compounded index | Use only supported explicit contracts; no invented adjustments |
| Direct FX / no basis | No inverse/cross synthesis; portfolio/collateral conversion needs exact direct orientation | Supply exact direct pair/settlement and supported funding assumption |
| Zero-knot risk, explicit finite bumps | Not market-quote DV01; truncation/cancellation depends on h | State scope/signs, test meaningful bump stability |
| Additive XVA / restricted comparative CCR | Unilateral deterministic-discount CVA/DVA, residual funding proxy and external IM omit bilateral/default/recursive economics | Read Phases 7/8 assumptions; no regulatory capital/compliance claim |
| No validation lab/mutation/governance persistence | Current tests are not independent institutional approval or model inventory | Phases 9–11 planned |
| Operational API only, unauthenticated local service | No production risk jobs, authorization, scale/HA or security certification | Loopback/development use; Phase 12 planned |
| Incomplete automatic lineage | Simulation captures sequences/runtime/platform and optional supplied source revision; portfolio/market/curve/ledger/pricer hashes exist in memory; persisted lineage absent | Preserve external source/runtime evidence; phased lineage work |
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

## Phase 5 scope

Legal enforceability is caller attestation. Cash collateral only; signed haircuts
use a symmetric research convention. IA is reusable title-transfer collateral,
not segregated regulatory IM. Calls are effective-value instructions; physical
allocation/rounding/confirmed movements are supplied explicitly. No failed settlements,
interest, disputes, securities, funding, liquidation or custody is modeled. Calendar
frequency/lag/MPOR ignores business calendars. End-of-day whole-trade termination
requires exit cash separately. Direct FX orientation and precision/horizon contracts
restrict supported books. See [full assumptions](methodology/PORTFOLIO_COLLATERAL.md).

## Phase 6 exposure and credit scope

Conditional Q model curves use supplied knots and log-linear discount interpolation;
projection shares the bound currency curve. Q labels/correlation alone cannot establish
stochastic-rate FX no-arbitrage: drift consistency is caller responsibility. Origin
fixings must be supplied; future fixings inside horizon must be on the exact grid.
Derived snapshots are model values with synthetic labels, not observed market data.

Cash margin simulation assumes perfect scheduled settlement in zero-haircut CSA currency
on a daily calendar grid. Output cap covers retained exposure matrices only, not peak
memory. Exact empirical PFE requires all exposure paths; no profile confidence intervals
or distributed computation are provided. EPE is full-horizon trapezoidal EE, not effective EPE.

EAD uses right grid endpoints of alive-path collateral. Default-conditioned freeze of
calls/settlement, interpolation at default and MPOR closeout are absent. It is not
regulatory EAD/CVA and can be biased near maturity. Static rank stress is full-path,
non-adapted and only preserves the finite sampled default marginal. Dynamic credit
uses left-grid GBM spread intensity and credit-triangle assumptions with no baseline
survival calibration, stochastic recovery, bilateral defaults or CDS model. See
[exposure](methodology/EXPOSURE.md), [credit](methodology/CREDIT_DEFAULT.md),
[WWR](methodology/WRONG_WAY_RISK.md). Phase 7 separately converts grid EAD into sampled discounted losses with these same limitations.

## Phase 7 XVA and risk scope

Unilateral CVA/DVA sum without joint first-to-default closeout. Discounting is a
supplied deterministic origin curve, excluding stochastic discount covariance.
Independent loss uses endpoint-average quadrature; dependent loss discounts actual
right-grid EAD with alive collateral, omitting default freeze/MPOR. Estimator and
marginal changes make direct independent/dependent differences unsuitable as isolated
WWR attribution. Exposure/XVA Monte Carlo confidence intervals are not reported.

Funding uses alive residual borrowing/lending proxies without hedge/default/recursive
cash economics. Spreads may economically overlap credit adjustments; automatic
avoidance of double counting is not claimed. Segregated posted IM is external,
separate from CSA IA and held fixed with funding during risk bumps; no regulatory IM
estimator or settlement exists. All boundaries reject invalid inputs without repair.

Risk supports explicit Vasicek/HullWhite/GBM transformations and continuous CSA
receive threshold. Heston vega, calibrated quote CS01, custom dynamic-policy credit
bumps, shared single-name spread shifts and discrete CSA derivatives are unsupported.
Common streams do not guarantee stable differences in default buckets or at exposure
kinks. Sequential attribution is order dependent and always retains the actual-end
residual. Capital remains outside the XVA layer; Phase 8 adds restricted CCR research. Governance/lab and financial production endpoints remain deferred.
[Detailed formulations](methodology/XVA.md), [funding](methodology/FUNDING_MARGIN.md),
[risk](methodology/XVA_SENSITIVITIES.md).

## Phase 8 CCR scope

Domestic vanilla zero-spread/unit-gearing IRS and domestic-quote FX only; other
contracts/asset classes reject. IR offsets stop at currency/maturity bucket.
Explicit same-day direct FX conversion, single reporting currency across legal
sets, daily receive-capable CSA and independently supplied business-day MPOR/NICA
restrict scope. No collateral eligibility/segregation/legal opinion, clearing,
dispute/large-set adjustments, multiple CSA or full jurisdictional rulebook.

Actual Q exposure yields a research IMM challenger, not approved current/stressed
IMM. Exact horizon nodes, right-endpoint normalized averages, finite samples,
no rollover and alive-path margin without default-frozen regulatory MPOR remain
limitations. Serial legal-unit replay scales runtime; output budget is per unit.
Caller weights/ratio give illustrative capital inputs only. Arithmetic attribution
and comparison exceptions do not create causal explanations or governance Findings.
[Standardized](methodology/STANDARDIZED_CCR.md),
[challenger](methodology/IMM_CHALLENGER.md), [comparison](methodology/CCR_COMPARISON.md).

Phase 8 mapping rejects scheduled future termination/reset contracts. The
explicit MPOR must meet the configured business-day floor. The application
checks simulation-request metadata, dates, profile units/path count and path shape
in addition to book/run/market/account evidence; each scope retains runtime
simulation metadata for replay.
