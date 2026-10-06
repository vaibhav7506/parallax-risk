# ADR 0002 — Money representation

**Status:** Accepted. **Recorded:** 2026-10-01; reflects Phases 1–2.

## Context
Currency amounts need stable signs, explicit currencies and exact primitive
arithmetic. Quantitative discounting also needs a declared numerical precision model.

## Decision
`Money` contains finite Decimal currency units and an explicit Currency. Primitive
arithmetic uses a private 34-digit context and traps inexact results. Pricing
explicitly converts amounts to checked binary64, then reports Decimal(str(value)).
No implicit FX conversion, cent rounding or exact-decimal valuation claim is made.

## Alternatives considered
Binary floats everywhere simplify numerics but blur exact amount arithmetic.
Integer minor units require currency/settlement rounding policy currently absent.
Decimal throughout pricing complicates interoperability and exponential numerics.

## Why this decision
Separate primitive and pricing precision contracts prevent the reporting container
from giving a misleading impression that numerical valuation is exact.

## Consequences
Cross-currency addition fails. Precision/range loss raises explicit errors; prices
remain unrounded currency units. Receivables are positive, payables negative.

## Risks
Users may confuse Decimal output with Decimal computation, or round prematurely.
Minor-unit and settlement conventions are NOT IMPLEMENTED.

## Follow-up
Any new rounding/reporting policy needs its own documented convention and tests.

## Related code
`src/parallax_risk/common/money.py` (`Money`),
`src/parallax_risk/domain/pricing/_numbers.py` (`money_value`, `priced_money`),
`tests/unit/test_primitives.py`, `tests/unit/test_pricing_contracts.py`.
See [methodology](../methodology/deterministic-pricing.md).

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Explicit Decimal amounts/currencies and exact primitive arithmetic | [Phase 1](../validation/phase-1.md) |
| 2 | Explicit binary64 pricing conversion and unrounded Decimal reporting added | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Separate canonical ADR created; arithmetic unchanged | [Register](README.md) |
| 3 | Reviewed; no Money change; model prices/residuals have explicit binary64 units | [Phase 3](../validation/phase-3.md) |
| 4 | Reviewed; no Money change; simulation buffers and statistics declare binary64 units and no settlement guarantee | [Phase 4](../validation/phase-4.md) |
