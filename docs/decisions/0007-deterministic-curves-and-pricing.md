# ADR 0007 — Deterministic curves and pricing

**Status:** Accepted. **Recorded:** 2026-10-01; implemented in Phase 2.

## Context
Reliable cash-flow pricing and sensitivity evidence must precede stochastic repricing.
Implicit conventions, missing fixings and mixed discount/projection assumptions can
produce plausible but financially wrong prices.

## Decision
Use explicit immutable curve assignments/schedules, positive anchored discounts,
linear or log-linear interpolation, declared extrapolation and checked binary64
discounting. Separate observed fixings from projected forwards. Bootstrap supported
deposit/par-swap quotes with bounded bisection and final repricing. Record each flow,
input hashes, model assumptions/version and central finite-difference bump scope/signs.

## Alternatives considered
Inferred market conventions shorten research scripts but hide assumptions. External
pricers add integration/dependency requirements. Decimal-only numerics change the
numerical stack; optimized solvers add complexity before a measured bottleneck.

## Why this decision
Auditable formulas and failure gates matter more than early performance. Independent
analytical targets and explicit negative-rate/settlement checks establish a baseline.

## Consequences
Negative rates are valid through positive increasing discounts. Known fixings never
fall back to curves. Zero-knot PV01 differs from market-quote DV01. FX parity accounts
for the spot value date. Every valuation contains reconciled signed contributions.

## Risks
Interpolation/extrapolation and finite-difference bumps introduce model/numerical
choices. Synthetic data are not observed prices; dirty bond PV is not clean price.

## Follow-up
Use the [methodology](../methodology/deterministic-pricing.md) for equations, units,
tolerances, assumptions and limitations. Stochastic, exposure and XVA work is DEFERRED.

## Related code
`src/parallax_risk/domain/market/curves/bootstrap.py` (`bootstrap_discount_curve`),
`src/parallax_risk/domain/market/curves/term_structures.py` (`DiscountCurve`, `CurveSet`),
`src/parallax_risk/domain/pricing/engine.py` (`DiscountingEngine`, `forward_fx_rate`),
`src/parallax_risk/domain/pricing/sensitivities.py` (`parallel_rate_sensitivity`, `fx_delta`),
`tests/quantitative/test_deterministic_pricing.py`.

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable; no financial pricing implementation | [Phase 1](../validation/phase-1.md) |
| 2 | Curves/bootstrap, contracts/pricing, zero-knot/FX risk and benchmarks introduced | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Canonical record and learning/navigation docs added; formulas unchanged | [Register](README.md) |
| 3 | Reviewed; deterministic-discounting model remains 0.2.0; stochastic pricing uses separate model primitives | [Phase 3](../validation/phase-3.md) |
