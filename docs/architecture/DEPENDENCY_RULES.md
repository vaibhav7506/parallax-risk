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
simulation/validation/governance folder just because a diagram describes planned
workflow. Keep research examples calling production modules. No import-time IO,
global mutable settings, random generator or cached financial state is acceptable.

Review this file and [ADR 0001](../decisions/0001-clean-architecture.md) whenever
dependency ownership changes; record the change in the phase history.
