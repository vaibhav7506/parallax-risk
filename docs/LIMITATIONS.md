# Current limitations

These limitations apply through Phase 12 research/service scope. Preserve them until an actual
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
| Authenticated research governance | Static API key/RBAC does not confer institutional approval or signed identity | Explicit roles/authority binding; enterprise identity/signatures absent |
| Bounded local asynchronous service | No HA, distributed implementation, wall-time cancellation or automatic crash recovery | Durable claims, explicit ownership/admission and operator inspection |
| Optional source/calibration provenance | Service retains exact request/result/lineage; unavailable commit remains null; linked deployment supports Vasicek only | Explicit evidence and assumptions; no invented reference |
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
residual. Capital remains outside the XVA layer; Phase 8 adds restricted CCR research. Governance and financial production endpoints remain deferred; Phase 9 adds a scoped library lab.
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

## Phase 9 validation limitations

Same-case schema comparisons and findings are research evidence, not approval.
Independent flat-hazard/discount CVA benchmarks do not validate every XVA assumption.
Fixed cash offsets are not general dynamic CSA monotonicity. Finite grid/path ladders
do not prove convergence or bound bias; step mappings are not Brownian-nested.
Single Sobol point confidence and dependent CVA observations reject in this adapter.
Bootstrap is conditional approximate coverage, parameter ensembles are supplied ranges,
calibration delta bands are local normal approximations and unavailable/constrained
covariance rejects. Caller-sourced history is not independently authenticated.
No QuantLib/ORE verification, historical market dataset, model approval, monitoring,
mutation/adversarial work or new financial API is claimed.
[Detailed lab assumptions](methodology/MODEL_VALIDATION.md).

## Phase 10 interpretation limits

The 15 built-in faults target isolated synthetic operation seams; they do not mutate
all source branches or implement missing default-conditioned MPOR. Dated calibration
selection and reduced sampling diagnostics are limited probes. Equivalent and
unexercised mutants remain misses. Reported rates apply only to retained cases/faults/checks.

Search bounds/linear restrictions express caller-declared plausibility; complete
financial constructors can still reject a candidate. No repair/penalty/fallback is
applied. Optimizer stopping does not prove a global maximum. The XVA challenger
shares production exposure and supports independent credit only. Fixed-stream finite
samples/grid integration and optimizer selection remain limitations.

Forensic fingerprints/ordered bridge labels overlap and are not causal proof.
Actual repeatability does not establish accuracy. Calibration provenance is caller
supplied, and hashes alone cannot reconstruct complete cases. Detailed
[mutation](methodology/QUANTITATIVE_MUTATION.md), [search](methodology/ADVERSARIAL_SEARCH.md),
[forensics](methodology/FAILURE_FORENSICS.md).

## Phase 11 bounds

GovernedXva persists lineage; lower-level numerical research calls are ungoverned.
Input bytes/path buffers and calibrated result repositories are not persisted;
retain artifacts behind hashes. Source revision/calibration ID are explicit caller
references and may be null. Actors/authority are not authenticated/signed. Raw DB
admin tampering is outside append-only guarantees. Policies/review dates/monitor
observations/narratives are caller-owned; no scheduled collection, external alert
delivery, automatic approval/closure or PDF exists. Thresholds are scalar, strict
exceedance in declared units; no hidden relative/vector aggregation. Existing
financial limitations remain. [Detailed contracts](methodology/GOVERNANCE.md),
[actual verification status](validation/phase-11.md).

## Phase 12 current service scope

The 0.12.0 service adds authenticated versioned financial/lab/governance jobs,
retained inputs/results/lineage, owner-scoped objects/reports and production CLI.
Earlier phase-specific descriptions above record their scope at introduction; current
service behavior is defined by [service contracts](methodology/SERVICE.md),
[operations](operations/SERVICE.md) and
[Phase 12 evidence](validation/phase-12.md). Numerical model limitations remain applicable.
