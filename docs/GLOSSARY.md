# Financial and engineering glossary

| Term | Intuition / why it matters | Current project usage and reference |
|---|---|---|
| Counterparty credit risk (CCR) | Risk of losing a positive derivative claim when the other party defaults | Project mission; exposure/default calculation NOT IMPLEMENTED; [roadmap](../ROADMAP.md) |
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
| Seed / random sequence | Seed initializes a chosen algorithm; a sequence also depends on stream/order/version | Only seed metadata implemented; RNG/streams deferred to research phases; [ADR 0004](decisions/0004-random-sequence-reproducibility.md) |
| Correlation / PSD | Dependence must yield nonnegative variances for the complete joint matrix | Strict structure, eigenvalue diagnostics and singular policy; [correlation](methodology/CORRELATION.md) |
| Monte Carlo | Estimate quantities from repeated simulated scenarios | NOT IMPLEMENTED; Phase 4 planned; [roadmap](../ROADMAP.md) |
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
