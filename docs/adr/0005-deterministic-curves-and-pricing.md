# ADR-0005: Explicit immutable deterministic pricing inputs

**Status:** Accepted
**Date:** 2026-10-01
**Deciders:** Parallax Risk implementation (institutional review pending)

## Context
Phase 2 needs reproducible deterministic prices and diagnostics before stochastic
models are introduced. Rates, curve construction, historical fixings, settlement
and sensitivity units can otherwise be inferred inconsistently.

## Decision
Keep market observations, curves and instruments as independent frozen domain
values. Validate external market data with Pydantic at the application boundary.
Hash identities, conventions, values and provenance using canonical schema-1 JSON.
Use explicit discount and index projection assignments, declared interpolation and
extrapolation, supplied schedules and mandatory known fixings. Perform deterministic
binary64 pricing with finite/range checks and immutable cash-flow reconciliation.
Use bounded bisection for sequential deposit/par-swap bootstrapping, recording actual
repricing residuals and numerical settings. Financial API/CLI integration remains
in its prescribed Phase 12.

## Options considered

| Option | Complexity | Cost | Scalability | Familiarity |
|---|---|---|---|---|
| Immutable typed Python domain with explicit conventions | Moderate | Low runtime overhead | Local deterministic library | Standard quantitative Python |
| Market-data objects that infer curves and conventions | Low initially | Hidden convention/model coupling | Difficult reproducibility | Convenient research pattern |
| Delegate all valuation to an external pricing system | Integration complexity | External runtime/dependency | Vendor dependent | Established industry tooling |

## Trade-off analysis
Explicit inputs require more caller code but make missing data and valuation
assumptions visible. Binary64 matches the deterministic numerical stack and can be
benchmarked against independent high-precision formulas; Decimal wrappers describe
reporting values, not exact quantitative arithmetic. Bisection is slower than an
optimized solver but bounded and transparent at this scale. No performance claim
or external-pricer equivalence is made.

## Consequences
Callers construct curves separately from snapshots and must provide calendar-adjusted
payment dates. Negative rates are supported through positive increasing discounts.
Continuous-zero knot risk differs from market-quote risk, and is named/documented
accordingly. Volatility and credit observations are recorded without premature
surface calibration, hazard conversion or stochastic models.

## Action items
1. [x] Add analytical, rejection, property, regression and replay tests.
2. [x] Document signs, settlement rules, precision and numerical gates.
3. [x] Keep data examples explicitly synthetic and retain Phase 1 evidence.
