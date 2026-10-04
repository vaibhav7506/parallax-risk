# Parallax Risk: deterministic curves and pricing

Phase 2 model version **0.2.0**, `deterministic-discounting`. This is a documented
implementation scope, not a certification or regulatory-compliance claim.

## Market representation and provenance

Market snapshots are frozen, versioned daily observations with valuation date,
explicit currency universe, generic quotes, annual rates, direct FX spots,
volatility, credit spreads and historical index fixings. Observations have a typed
quote ID, source name/reference, aware UTC observation timestamp and mandatory
sample flag. Numeric inputs must be finite; booleans and numeric strings are
rejected. Pydantic ingestion forbids extra fields and converts input lists to
immutable tuples. Civil dates require date objects or YYYY-MM-DD text; numeric
epoch timestamps and noncanonical date text are rejected. Observation instants
require explicit timezone-bearing timestamps. Empty optional categories are permitted; a snapshot must contain
at least one observation. Required missing pricing inputs raise explicit errors.

Source UTC date cannot follow valuation date; rate/credit maturities and volatility
expiries must be future; known fixings cannot be future; spot settlement cannot
precede valuation. This is a daily cutoff, not an intraday exchange/source-timezone
policy. Historical stale data is recorded as supplied; there is no inferred freshness
threshold or live vendor integration. Duplicate IDs and observation keys are invalid.
Only one orientation per FX pair is accepted. Inverse/cross-rate synthesis is absent.

Currencies and observations are canonically ordered. Schema-1 SHA-256 JSON digests
include typed identities, version, dates, conventions, values and complete source
metadata. Snapshot, curve-set and instrument hashes accompany each price. Changing
an input version changes its hash. Updating FX creates a new explicitly versioned
snapshot. Hashes provide reproducible content identity, not signatures or authenticity.
The fixture under `data/sample` is entirely hand-specified synthetic data.

## Curves and time

Annual rates are decimal units: 0.05 means 5%, and one basis point is 0.0001.
Civil-date curve times use the curve's declared day count. Coupon accruals use the
contract's declared day count, which may differ. All curves have exact t=0 anchor,
strictly increasing finite times and aligned immutable nodes. Discount factors are
strictly positive with D(0)=1. Negative rates and D(t)>1 are valid; decreasing
discounts are a diagnostic, not a universal constraint. Diagnostics report extrema,
increasing intervals and knot continuous zero rates.

For weight w between adjacent nodes, linear interpolation is
`y=(1-w)*y_left+w*y_right`; log-linear positive interpolation is
`y=exp((1-w)*log(y_left)+w*log(y_right))`. These definitions agree with
[Strata's interpolation documentation](https://strata.opengamma.io/apidocs/com/opengamma/strata/market/curve/interpolator/CurveInterpolators.html).
Discount curves allow either declared strategy; log-linear discounts give piecewise
constant continuous forwards. Zero curves interpolate quoted annual zero rates
linearly with explicitly declared simple, continuous or periodic compounding.
Sampling a zero curve into a discount curve preserves knot discounts but may change
values between knots. No representation-equivalence assumption is hidden.

Extrapolation is explicit: `error` rejects requests beyond the last node.
Discount-curve `flat_zero` holds the terminal continuous zero rate; zero-curve
`flat_zero` holds its terminal quoted rate with its declared compounding. Past-date
and negative-time requests are invalid. A zero rate at t=0 is intentionally undefined.
An index projection curve gives the simple forward
`L(start,end)=(D_projection(start)/D_projection(end)-1)/alpha`.
Discount and projection curves may differ; neither substitutes for a missing one.

## Bootstrap and diagnostics

The framework supplies a typed quote protocol, immutable inputs/settings, a positive
discount bracket, bounded sequential bisection and all-quote final repricing. Phase 2
supports a simple deposit starting at valuation date and a constant-notional,
single-curve par swap starting there, with zero floating spread and payments at
accrual ends. Deposit rate is `(1/D(T)-1)/alpha`. Par swap rate is
`(1-D(T))/sum(alpha_i*D(T_i))`. Payment schedules and day counts are supplied.
Missing earlier coupon nodes are interpolated by the explicitly chosen strategy.

Quote maturities must already be strictly ordered and unique; no sorting, lag,
basis, futures convexity or invalid-quote repair is inferred. Single-curve quote
bootstrapping does not calibrate heterogeneous discount/projection curves or market
cross-currency basis. Those features are outside this deterministic implementation.

| Numerical setting | Default and unit |
|---|---|
| Positive DF bracket | [1e-8, 10], dimensionless |
| Final quote residual gate | absolute 1e-12, decimal annual rate |
| DF convergence gate | max(absolute 1e-13, relative 1e-12 * scale), dimensionless |
| Iteration limit | 200 per solved node |

Interior roots require both residual and bracket-width convergence; endpoint roots
within the residual gate are accepted directly. Bracket failure, iteration exhaustion,
binary64 stagnation or final repricing failure raises without a partial result.
Bounds are a numerical search domain, not economic plausibility limits. Diagnostics
contain actual observed/model rates, signed residuals and iteration counts; result
includes inputs hash, curve and exact settings.

## Cash flows, bonds and swaps

Known payment PV is `signed_amount*D_discount(payment_date)`. Receivables are
positive and payables negative. Fixed coupon amount is `N*r*alpha`; simple floating
amount is `N*(gearing*L+spread)*alpha`. Fixing on/before valuation date requires an
observed fixing even when projection exists; future fixing uses the explicit index
projection curve. Known fixings stay fixed under rate bumps. Historical accrual
periods with an unpaid coupon are supported through observed rates. Fully paid
coupons require no fixing/projection lookup.

Caller supplies civil accrual bounds, adjusted payment and fixing dates, day counts,
direction and index. Schedules are nonempty, contiguous and increasing with payment
on/after accrual end. Simple index fixings occur on/before accrual start. No calendar,
business-day lag, compounding, in-arrears convexity or official index convention is
invented. Same-day payments are excluded by default and included only when the
explicit context policy is true. Earlier payments are always excluded.

Zero-coupon bonds contain one default-free long redemption. Fixed bonds contain
coupons and redemption on the last supplied payment date, with dirty PV; there is
no clean-price/accrued-interest, issuance-price, default, optionality or ex-coupon
adjustment. Face/notional is nonnegative, including zero. Signed standalone coupons
permit negative notionals. Negative coupon/index rates are supported.

Pay-fixed swap PV is floating-leg PV minus fixed-leg PV; receive-fixed reverses the
sign. Both schedules share contractual start/end but may differ in frequency, day
count and payment dates. There are no principal exchanges. For a single-curve swap
with matching, no-lag schedules and initial fixing equal to the first implied forward,
the par formula above gives zero PV. Dual-curve par rate is discounted projected
floating coupons divided by fixed-leg discounted accrual annuity. The use of summed
leg PV and zero-PV par rate follows standard deterministic discounting as described
by [Strata's swap pricer](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/swap/DiscountingSwapProductPricer.html).

Each result contains NPV Money, reporting currency, valuation date, model name/version,
assumptions and sorted cash-flow contributions: original signed amount, payment date,
discount, FX conversion, reporting-currency PV, curve ID and rate origin. Summing these
contributions with compensated binary64 summation reconciles the reported NPV.

## FX forward, spot settlement and parity

Spot `S(s)` is QUOTE currency units per BASE unit for explicit settlement date s.
For a buy-base forward receive N BASE and pay N*K QUOTE at T>=s. Reporting currency
is QUOTE; sell-base reverses both signs. Under the deterministic, frictionless common
funding/no-basis assumption:

```
S(0) = S(s) * D_quote(s) / D_base(s)
F(T) = S(0) * D_base(T) / D_quote(T)
PV_quote = N*S(0)*D_base(T) - N*K*D_quote(T)
```

The settlement-date conversion follows directly by discounting the spot exchange's
two payments and requiring zero PV. At K=F(T) the forward has zero PV. Discount each
payment in its own currency, consistent with the
[Strata FX pricer](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/fx/DiscountingFxSingleProductPricer.html).
This reference is methodological; the tests do not claim externally executed Strata
benchmarks. There are no FX points, basis calibration, transaction costs, inverse
quote fallback or multi-currency portfolio conversion. Quotes with settlement before
valuation and future forward maturity before spot settlement are rejected.

## Finite differences, precision and acceptance tests

Caller declares positive central bump h and selected unique curve IDs. Every
assignment of a shared ID is bumped consistently. Continuous-zero knot shift b
changes `D_i` to `D_i*exp(-b*t_i)`. With log-linear discounts this is an exact
parallel continuous-zero shift between knots; with linear discounts it is a knot
shift. Quotes/fixings remain fixed: this is **zero-knot risk**, not market-quote DV01.

```
rate_derivative = (PV(+h)-PV(-h))/(2*h)
PV01 = rate_derivative * 0.0001
DV01 = -PV01
FX_delta = (PV(S+h)-PV(S-h))/(2*h)
```

PV01 is signed NPV change for an upward basis point to first order. DV01 uses the
opposite sign by this project's explicit convention, not absolute value. FX delta
is QUOTE-currency PV per one QUOTE/BASE spot-rate unit with curves fixed, including
settlement-date conversion. Invalid/nonpositive FX shocks, bumps below binary64
resolution and numerical range failures raise explicitly. Central differences have
truncation and cancellation error; no automatic bump is inferred.

Input Money uses Decimal, but deterministic quantitative operations explicitly
convert to binary64. Finite outputs become `Decimal(str(value))`, without cent or
settlement rounding. This reporting wrapper does not imply exact-decimal valuation.
Overflow, nonzero underflow and NaN/Inf are rejected at numerical boundaries.

Tests use independent 50-digit Decimal exponential formulas, hand-derived deposit/
swap discounts, single/dual-curve par values, FX parity including two-day settlement,
direction reversal and cash-flow summation. Formula checks use explicit per-case
absolute/relative bounds near 1e-12 currency units for small notionals and 1e-14
relative for exponential discounts; million-unit FX cases allow 1e-8 currency units
and 1e-12 relative to account for cancellation. Central-difference rate derivative tests allow
1e-8 relative with h=1e-4 (documented truncation bias); FX's linear spot derivative
uses 1e-10 relative. Property tests constrain rates/notionals to finite economically
readable domains; monotonicity is asserted only under nonnegative flat rates.
This deterministic-discounting model contains no stochastic/pathwise calculations.
Separate [Phase 3 models and calibration](INDEX.md) are implemented; random paths,
exposure and XVA remain NOT IMPLEMENTED.
