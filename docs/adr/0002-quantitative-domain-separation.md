# ADR-0002: Immutable quantitative primitives with explicit conventions

**Status:** Accepted
**Date:** 2026-09-30
**Deciders:** Parallax Risk implementation (institutional review pending)

## Context
Money, dates and tolerance semantics must remain consistent across future models.
Implicit float conversion, holiday assumptions and silent rounding obscure errors.

## Decision
Use frozen standard-library dataclasses and nominal identifiers. Money requires
finite Decimal and Currency; exact arithmetic uses an isolated 34-digit context
with precision-loss traps. Scalar convention formulas use validated finite floats.
Pydantic validates boundary configuration/responses, not core primitive classes.
Every financial convention is an explicit enum; holidays are supplied by the caller.

## Options considered
| Option | Complexity | Cost | Scalability | Familiarity |
|---|---|---|---|---|
| Immutable dataclasses plus boundary schemas | Moderate | Low | Numeric arrays can be introduced separately | Standard Python |
| Pydantic models throughout all numerical code | Low initial | Conversion/validation overhead | Additional array integration needed | Common API pattern |
| Bare floats/strings/dicts | Low | Hidden ambiguity and weak contracts | Fast scalar operations | Universal primitives |

## Trade-off analysis
Decimal protects monetary input arithmetic but is unsuitable for large future
simulation arrays. Finite float operations and model-specific tolerances will be
separate from exact Money and must document conversion policies when introduced.

## Consequences
No implicit FX or settlement rounding. Unsupported conventions fail explicitly.
Calendars do not imply official holiday coverage. Future model cards must declare
units, conventions and tolerances rather than inherit foundation defaults blindly.

## Action items
1. [x] Implement and test exact/frozen primitive contracts.
2. [x] Document formulas, precision limits and supported convention subset.
