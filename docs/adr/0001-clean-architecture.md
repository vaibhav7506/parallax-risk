# ADR-0001: Inward dependency direction in a modular src package

**Status:** Accepted
**Date:** 2026-09-30
**Deciders:** Parallax Risk implementation (institutional review pending)

## Context
The same primitives will serve research, CLI and HTTP workflows. Phase boundaries
prohibit early financial implementations. Import safety and test isolation matter.

## Decision
Use `src/parallax_risk` with common primitives, application ports/configuration,
infrastructure adapters, API and CLI composition roots. Create directories only
when implemented. Domain values never depend on HTTP or ORM frameworks.

## Options considered
| Option | Complexity | Cost | Scalability | Familiarity |
|---|---|---|---|---|
| Modular package with inward dependencies | Moderate | Low deployment overhead | In-process initially | Conventional Python |
| HTTP-centric monolith | Low initially | Increasing coupling cost | Controller-bound workflows | Familiar web pattern |
| Microservices per quantitative module | High | High operations cost | Independent deployment | Requires distributed operations |

## Trade-off analysis
A modular package supports reuse without introducing network boundaries before a
measured need. Explicit composition is more verbose than global service singletons.
Python cannot enforce architecture alone, so AST dependency tests guard the layers.

## Consequences
Quantitative and boundary tests can run independently. Later workflows need
explicit dependency injection. Distributed execution is deferred to Phase 12.

## Action items
1. [x] Create only Phase 1 modules and architecture dependency tests.
2. [x] Document composition and import-safety rules.
