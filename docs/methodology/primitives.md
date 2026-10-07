# Primitive conventions, assumptions and limitations

All financial inputs require declared conventions. No market data or quantitative
benchmark measurements are fabricated. The unit tests below use exact arithmetic
examples derived from the formulas, not measured risk-engine results.

## Money and currencies

Money uses `Decimal` currency units, not cents. Receivables/assets are positive,
payables/liabilities negative. Inputs must be finite Decimal, with explicit
Currency. No float conversion, FX inference or rounding occurs. Arithmetic uses
a private 34-digit decimal context and traps inexact results/overflow; ambient
process decimal precision never changes behavior. Exact input digits are retained;
operations exceeding arithmetic precision raise NumericalError. Currency enum
supports USD/EUR/GBP/JPY/CHF/CAD/AUD/NZD/INR/CNY only. Minor-unit rounding and the
complete ISO registry are unsupported. Example: USD 0.1 + USD 0.2 = USD 0.3 exactly.

## Time and calendars

Civil dates exclude time/timezone. Instants require explicit timezone and normalize
to UTC. Accrual intervals use [start,end); reverse order returns the negative
fraction. Date grids are nonempty and strictly increasing. Calendar holiday and
weekend sets are immutable, supplied by the caller, and deliberately not marketed
as official holiday databases. Monday=0; the default weekends are Saturday/Sunday.
All-weekend calendars are rejected. Date-range overflow is explicit. Custom
BusinessCalendar implementations must provide reachable open dates; there is no
assumed global holiday feed.

Following/preceding roll to the next/previous business day; modified forms reverse
direction if rolling crosses a month boundary. Unadjusted preserves the date.
Business-day offsets exclude the start; zero preserves it, including a holiday.

## Day counts

| Convention | Formula | Deliberate restriction |
|---|---|---|
| ACT/360 | actual days / 360 | Calendar days, not business days |
| ACT/365F | actual days / 365 | Leap-year denominator remains 365 |
| ACT/ACT ISDA | sum of days in each calendar year / (365 or 366) | No coupon schedule; not ICMA |
| 30E/360 | (360*year difference + 30*month difference + clipped-day difference)/360 | Both days clipped to 30; no February end/maturity adjustment |

Definitions are distinguished using the [ISDA day-count material](https://www.isda.org/2008/12/22/30-360-day-count-conventions/)
and the [OpenGamma Strata reference](https://strata.opengamma.io/day_counts/),
an independently maintained implementation reference. The 30E/360 European
variant must not be substituted for US 30/360 or 30E/360 ISDA.

Hand-derived examples: 2024-01-01 to 2025-01-01 has 366 days, so ACT/360 is 366/360,
ACT/365F is 366/365, ACT/ACT ISDA is 1. For 2023-12-31 to 2024-01-02, ACT/ACT ISDA
is 1/365 + 1/366. 2024-01-31 to 2024-02-29 is 29/360 under European 30E/360.

## Compounding and tolerances

Rates are decimal annual rates (0.05 means 5%), time is a nonnegative declared
year fraction. Simple accumulation is 1+r*t; continuous is exp(r*t); periodic is
(1+r/m)^(m*t), with explicit positive integer frequency m. Positive finite factors
are required. Negative rates are allowed in their mathematical domain. No curve,
instrument valuation or XVA calculation lives in these primitive helpers; Phase 2
valuation uses them under the [deterministic model](deterministic-pricing.md). Non-finite outputs and
underflow to zero raise NumericalError; overflow is not silently clipped.

Foundation float comparisons use |a-b| <= max(atol, rtol*max(|a|,|b|)), implemented
with `math.isclose` after finite validation. Default atol=1e-12 and rtol=1e-9
cover dimensionless convention formula checks at ordinary scales; they are not
statistical confidence thresholds or tolerances for future monetary results.
Exact Decimal arithmetic uses exact equality. Formula benchmarks use declared
pytest tolerances. Hypothesis checks bounded mathematical invariants rather than
statistical estimates; these foundation helpers do not implement an estimator.
Phase 4 provides separate [Monte Carlo statistics](MONTE_CARLO_STATISTICS.md).

## Reproducibility

RunContext stores RiskRunId, aware UTC timestamp, uint64 seed and lowercase
SHA-256 digest. Canonical configuration uses sorted JSON keys, compact separators,
no NaN, and a schema-version marker. Secret credentials are excluded; database
presence and nonsecret operational settings are included. This is not a complete
market/portfolio/model lineage hash. Changing credentials alone preserves it.
Identity and timestamp are injected for exact envelope replay; new runs use fresh
UUIDs/current UTC, which must never supply randomness to quantitative models.
Different numeric results across software/BLAS versions remain possible later;
dependency locks and Phase 4 simulation environment metadata support that control.

Phase 5 portfolio/market/curve/ledger lineage is implemented in memory; persisted
governance lineage remains deferred. Phase 4 records explicit
sequence/environment metadata and an optional supplied source revision; these do not
prove input authenticity or mathematical correctness.

Phase 3 model/calibration primitives are separate from these helpers. Calibration
IDs, input/settings hashes and parameters now exist; Phase 4 implements random
sequences, while persisted governance lineage remains deferred. See [calibration](CALIBRATION.md).

Phase 5 reuses exact-contract Money for positions/cash/haircuts/aggregation, while
explicit binary64 FX factors become Decimal text. It does not imply exact-decimal
valuation; see [portfolio conventions](PORTFOLIO_COLLATERAL.md).
