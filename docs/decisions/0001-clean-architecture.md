# ADR 0001 — Clean architecture

**Status:** Accepted. **Recorded:** 2026-10-01; reconstructs Phase 1/2 decisions.

## Context
The same quantitative rules must support research, operational CLI and eventual
financial APIs without depending on HTTP or database availability.

## Decision
Use a modular typed Python src package with inward dependencies. Common primitives
are below domain; application validates inputs and injects workflows; adapters and
composition roots depend inward. Create modules only in their authorized phase.

Phase 3 model/objective values and numerical instrument formulas stay in domain.
CalibrationSolver is an application port; ScipyLeastSquares implements it in
infrastructure. NumPy/SciPy mathematical dependencies are permitted in domain;
application/HTTP/ORM dependencies remain forbidden.

## Alternatives considered
HTTP-centric calculation code is quick to start but couples financial tests to
web concerns. Microservices add deployment/network failure before a measured need.
The modular package costs explicit composition code but has low operating overhead
and independent domain tests; it is familiar Python rather than distributed tooling.

## Why this decision
Explicit ownership makes missing dependencies and resource lifetimes visible and
keeps quantitative invariants testable without frameworks.

## Consequences
Domain values are reusable. Boundaries perform conversion and require more caller
code. AST tests guard dependency direction; imports must remain side-effect free.

## Risks
Python cannot enforce the architecture by type checking alone; new imports can
introduce coupling. Global settings/caches would damage run isolation.

## Follow-up
Review dependency tests with new modules. Financial HTTP/CLI workflows are DEFERRED
to Phase 12. Do not scaffold those implementations now.

## Related code
`src/parallax_risk/domain/pricing/engine.py` (`DiscountingEngine`),
`src/parallax_risk/application/pricing.py` (`PricingService`),
`src/parallax_risk/api/app.py` (`create_app`),
`tests/integration/test_architecture.py`.
`src/parallax_risk/application/calibration.py`,
`src/parallax_risk/infrastructure/calibration/scipy_solver.py`.

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | src layout, common/application/adapter/composition boundaries introduced | [Phase 1](../validation/phase-1.md) |
| 2 | Domain market/contracts/pricing and application ingestion/workflow added; inward rules retained | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Canonical record created from historical ADRs; no calculation change | [Register](README.md) |
| 3 | Domain model/objective values, application calibration port and SciPy infrastructure adapter added; inward dependency rules retained | [Phase 3](../validation/phase-3.md) |
| 4 | Application engine port and research orchestration added; mathematical stream/kernel/observable contracts remain in domain | [Phase 4](../validation/phase-4.md) |
