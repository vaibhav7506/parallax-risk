# Financial and engineering glossary

| Term | Intuition / why it matters | Current project usage and reference |
|---|---|---|
| Counterparty credit risk (CCR) | Risk of losing a positive derivative claim when the other party defaults | Deterministic and pathwise exposure/credit research implemented; default loss deferred; [roadmap](../ROADMAP.md) |
| Model risk | Risk that assumptions, mathematics, data or implementation produce misleading decisions | Explicit assumptions and quantitative tests today; independent lab/governance deferred; [validation](validation/OVERVIEW.md) |
| XVA / CVA | Valuation adjustments; CVA addresses counterparty default losses | NOT IMPLEMENTED; no present default-loss result; [roadmap](../ROADMAP.md) |
| NPV / PV | Value today of signed future payments | DiscountingEngine/PricingResult; [pricing](methodology/PRICING.md) |
| Discount factor D(0,t) | Multiplier translating a payment at t into today's value | Positive anchored DiscountCurve; may exceed 1 with negative rates; [curves](methodology/CURVES.md) |
| Zero rate | Annual rate representing accumulation to one maturity | ZeroCurve declares time/day count/compounding; [curves](methodology/CURVES.md) |
| Forward rate | Rate implied for a future accrual interval by a projection curve | Simple rate `(D(start)/D(end)-1)/alpha`; [curves](methodology/CURVES.md) |
| Day count / accrual alpha | Rule converting civil dates to a year fraction | ACT/360, ACT/365F, ACT/ACT ISDA, European 30E/360; [primitives](methodology/primitives.md) |
| Fixing | Observed index rate on a contractual date | Mandatory for on/before-valuation fixing; never replaced by a projection; [pricing](methodology/PRICING.md) |
| Bootstrap | Construct curve nodes that reproduce declared instrument quotes | Bounded deposit/par-swap bisection and residual gate; [curves](methodology/CURVES.md) |
| Par rate / strike | Contractual rate/strike producing zero PV under the supplied inputs | Par swap and FX parity benchmarks; [pricing](methodology/PRICING.md) |
| Dirty bond PV | Value including all included contractual coupon/redemption payments | Current bond output; clean settlement price/accrued interest absent; [limitations](LIMITATIONS.md) |
| Basis point | 0.0001 in decimal annual-rate units | Rate sensitivity scaling; [sensitivity](validation/SENSITIVITY.md) |
| PV01 / DV01 | First-order price response to one basis point | Signed upward-rate zero-knot PV01; DV01 = -PV01; not market-quote risk; [sensitivity](validation/SENSITIVITY.md) |
| FX spot / QUOTE per BASE | Currency exchange amount per base unit for declared value date | Direct FxSpot; no inverse/cross inference; [market data](methodology/MARKET_DATA.md) |
| FX delta | Price change per one spot-rate unit | QUOTE-currency derivative with fixed curves and settlement conversion; [sensitivity](validation/SENSITIVITY.md) |
| Immutability / content hash | Preserve inputs and identify their complete content | Frozen snapshots/curves/contracts with schema-1 SHA-256; hashes are not signatures; [replay](REPRODUCIBILITY.md) |
| Seed / random sequence | Seed initializes a chosen algorithm; a sequence also depends on stream/order/version | Explicit addressed pseudo/Sobol sequences implemented in Phase 4; [ADR 0004](decisions/0004-random-sequence-reproducibility.md) |
| Correlation / PSD | Dependence must yield nonnegative variances for the complete joint matrix | Strict structure, eigenvalue diagnostics and singular policy; [correlation](methodology/CORRELATION.md) |
| Monte Carlo | Estimate quantities from repeated simulated scenarios | Phase 4 research engine; [methodology](methodology/MONTE_CARLO.md) |
| Calibration | Fit model parameters to sourced instrument observations under a bounded objective | Actual rate/Heston SciPy fits; bootstrap remains separate; [calibration](methodology/CALIBRATION.md) |
| Liveness / readiness | Process responds vs dependencies available | GET health/ready; a live service can be unready; [API](api/ENDPOINTS.md) |
| Q / risk-neutral measure | Pricing probability measure under which discounted tradable prices have the specified martingale dynamics | Rate/Heston models use Q parameters; not historical forecasts; [models](methodology/STOCHASTIC_PROCESSES.md) |
| Drift / diffusion | Expected instantaneous motion and sensitivity to shocks | Vector drift, independent-driver diffusion matrix; [contracts](methodology/STOCHASTIC_PROCESSES.md) |
| OU / mean reversion | Gaussian state returns towards a level | Vasicek/centered Hull–White; stable B(a,t) loading; [Vasicek](methodology/VASICEK.md) |
| Exact marginal transition | Correct one-step state distribution for supported constant coefficients | Excludes joint integrated-rate discounting; [contracts](methodology/STOCHASTIC_PROCESSES.md) |
| Euler–Maruyama / projected Euler | Approximate a differential equation with a finite time step | Heston projection is reported and biased; [Heston](methodology/HESTON.md) |
| Feller margin | Indicates whether the square-root variance zero boundary is accessible | 2*k*theta-xi² diagnostic; not imposed as a calibration constraint; [Heston](methodology/HESTON.md) |
| Characteristic function / Fourier inversion | Encode a distribution in complex exponentials and recover option values by integration | Heston stable Riccati/Lewis pricer with estimated-error gate; [Heston](methodology/HESTON.md) |
| Cholesky | Lower-triangular matrix mapping independent factors to declared covariance | Positive-definite resolved inputs only; [correlation](methodology/CORRELATION.md) |
| Scaled residual / RMSE | Model-minus-quote error divided by a declared scale; root mean squared error | Raw units and scaled units both reported; [calibration](methodology/CALIBRATION.md) |
| Jacobian rank / condition | Whether prices locally identify every fitted parameter and how sensitive inversion is | SVD evidence, uncertainty absent if inadequate; [calibration](methodology/CALIBRATION.md) |
| Active bound | A fitted parameter meets a configured lower/upper limit | Reported by optimizer; unconstrained covariance withheld; [calibration](methodology/CALIBRATION.md) |
| Local covariance | Linearized parameter uncertainty under an iid-scaled-residual assumption | Not global/model/market uncertainty or confidence guarantee; [calibration](methodology/CALIBRATION.md) |

New terms must be added with the phase introducing actual usage, not with fabricated
model classes or formulas for deferred modules.

## Terms introduced in Phase 4

| Term | Meaning and implemented use |
|---|---|
| StreamKey / substream | Root seed plus order-independent stream/substream IDs; [sequence policy](methodology/MONTE_CARLO.md) |
| PCG64DXSM | Explicit pseudo bit generator initialized by SeedSequence |
| Ziggurat normal transform | NumPy binary64 pseudo-normal sampler; version/build recorded |
| Sobol / LMS+shift | Scrambled low-discrepancy complete power-of-two quadrature design |
| Midpoint inverse-normal grid | Explicit finite-bit endpoint convention before ndtri; has quadrature bias |
| Antithetic pair | Adjacent reflected shocks whose pair average is one independent unit |
| Control variate | Adjustment using a separately fitted coefficient and known control expectation |
| Pilot | Separate explicitly addressed sample used to fit/freeze the control coefficient |
| Independent sampling unit | Path, pair average or scramble mean used for inference |
| Standard error | Estimated standard deviation of an estimator, separate from path dispersion |
| Student t interval | Approximate confidence interval over independent units |
| Scramble replicate | One independently randomized complete Sobol design |
| Path-count study | Nested counts with independent replicate RMSE/bias and descriptive slope |
| Frozen path buffer | Immutable little-endian C-order binary64 bytes exposed through read-only views |
| Traced peak allocations | tracemalloc peak for tracked allocations; not process RSS |

All statistical terms refer to [the implemented estimation policy](methodology/MONTE_CARLO_STATISTICS.md).

## Terms introduced in Phase 5

| Term | Meaning in this implementation |
|---|---|
| Portfolio snapshot | Versioned immutable legal book with full contract/lifecycle/CSA hash |
| Counterparty / legal netting set | Legal entity / separately attested scope for offsetting signed claims |
| Signed quantity / effective date | Position multiplier / contractual start metadata, not an activation gate |
| Gross vs net positive risk | Sum of positive trade values vs positive part of enforceably netted set value |
| CSA | Explicit research thresholds, direction, eligible cash and margin timing terms |
| VM / independent amount (IA) | Exposure-sensitive target / signed reusable title-transfer amount; not segregated IM |
| MTA | Full transfer occurs only when absolute difference is strictly greater than this amount |
| Settled / pending collateral | Physical cash held today / known future transfers included only for next call calculation |
| Haircut-adjusted value | Signed physical cash times (1-h), converted explicitly to agreement currency |
| MPOR | Caller-declared calendar freeze interval; deterministic closeout scenario, not default simulation |

Definitions, units/signs and caveats: [portfolio methodology](methodology/PORTFOLIO_COLLATERAL.md).

## Terms introduced in Phase 6

| Term | Declared meaning / scope |
|---|---|
| EE | Mean positive legal-scope exposure, including zero paths |
| ENE | Mean nonnegative payable exposure magnitude |
| EPE | Full-supplied-horizon trapezoidal time average of EE; not effective EPE |
| PFE | Configurable linear empirical quantile of positive path exposure |
| Grid EAD | Right-endpoint alive-path positive exposure for default; no default freeze/MPOR/regulatory alpha |
| Hazard / intensity | Nonnegative annual default rate; piecewise integration produces cumulative hazard |
| Survival | Probability alive conditional on surviving at origin; exp(-integrated hazard) |
| Recovery / LGD | Supplied constant fraction and complement; not applied to Phase 6 exposure |
| Cox threshold | Independent positive unit exponential, inverted against integrated intensity |
| Static rank WWR | Full-path non-adapted threshold reassignment preserving sampled marginal |
| Dynamic WWR | Correlated market/spread drivers and left-grid default intensity; no baseline calibration |
| Credit triangle | Declared approximation intensity = spread/(1-recovery) |
| Conditional market path | Model-derived curves/FX plus fixings known at each date |

[Definitions and units](methodology/EXPOSURE.md), [credit](methodology/CREDIT_DEFAULT.md),
[dependence](methodology/WRONG_WAY_RISK.md).
