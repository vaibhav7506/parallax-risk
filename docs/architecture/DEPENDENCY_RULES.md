# Dependency rules

Domain imports common and other domain modules. Common does not import domain,
application or adapters. Domain imports neither Pydantic, FastAPI nor SQLAlchemy.
Application uses domain and Pydantic boundaries, with abstract ConnectivityProbe;
it does not import HTTP/ORM/infrastructure. The PostgreSQL adapter implements that
port. API/CLI compose dependencies, while numerical logic remains inward.

Calibration adds an application CalibrationSolver port, implemented by infrastructure
ScipyLeastSquares. Domain owns objectives and analytical/Fourier pricing; NumPy/SciPy
mathematical routines are allowed there. Domain never imports the optimizer adapter.

`tests/integration/test_architecture.py` parses imports and also imports all package
modules in an isolated subprocess with settings/engine/logger initialization blocked.
Strict typing supplements these tests but cannot enforce architecture alone.

Add a module only when implemented in its authorized phase. Do not create a future
validation/governance folder just because a diagram describes planned
workflow. Keep research examples calling production modules. No import-time IO,
global mutable settings, random generator or cached financial state is acceptable.

Review this file and [ADR 0001](../decisions/0001-clean-architecture.md) whenever
dependency ownership changes; record the change in the phase history.

Phase 4's actual domain/simulation uses NumPy/SciPy numerical routines and common/domain
values. The application engine port and domain observable contract permit injection without importing
infrastructure. Research notebooks and execution/plotting dependencies live in the
optional development environment; production modules do not import notebook tooling.

Phase 5 domain/portfolio imports common plus existing domain contracts/pricing/market;
application/portfolio injects the pricer and logger. It never imports API/Pydantic/ORM
into the domain. Existing architecture checks exercise these new modules too.

Phase 6: Domain exposure/credit imports common and existing numerical/domain modules only. ExposureService composes domain values and injected ports; scripts/examples own logger/runtime composition. Import-side-effect checks automatically discover the new modules.
See [exposure workflow](../workflows/EXPOSURE_WORKFLOW.md).

Phase 7: domain/xva imports only common/existing domain mathematics. Application
owns calculator injection, input evidence checks and workflow composition. Import
and AST boundary tests discover these new modules; no HTTP/ORM dependency or global
RNG/logger/network initialization is added.

Phase 8 domain/ccr imports common and existing domain values, never HTTP/ORM/application. Application/ccr injects ExposureService; no import-time logger, settings, database or RNG is created.
[CCR workflow](../workflows/CCR_WORKFLOW.md), [decisions](../decisions/README.md).

## Phase 9 lab scope

Phase 9 domain validation depends only inward on common and existing domain mathematics/statistics; application composes injected services. Calibration solver imports occur in the explicit demo script composition, with no import-time fitting/I/O/network/RNG creation.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 applicability

The application defines SearchOptimizer and imports no infrastructure. infrastructure/validation implements it; scripts/demo_adversarial.py composes it. Domain evidence remains immutable and inward; imports perform no optimization, RNG initialization or I/O.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).
