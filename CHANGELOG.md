# Parallax Risk changelog

## 0.4.0 — Phase 4 complete — 2026-10-01

- Added explicitly addressed PCG64DXSM/Sobol normal streams, antithetics, separate
  pilot controls and replayable sequence/environment metadata.
- Added vectorized batched GBM/Vasicek/Hull–White/Heston paths with immutable buffers,
  correct Gaussian Brownian-driver covariance and explicit projection diagnostics.
- Added independent-unit estimates/intervals, convergence/path-count/variance studies,
  measured memory/vectorization harness and two executed production-calling notebooks.
- Reviewed all 11 canonical ADRs; added 0010/0011, accepted 0004's prior sequence policy.
  Created 8 and updated 46 Markdown documents; preserved historical phase evidence.
- Release/API/CLI advance to 0.4.0/phase 4; deterministic/calibration model versions
  remain 0.2.0/0.3.0. Docker helper uses scoped finally cleanup.
- Windows/Linux each passed 653 tests with real PostgreSQL and 99.15% coverage;
  packaging and ownership-checked cleanup passed. Complete evidence is recorded in
  [Phase 4](docs/validation/phase-4.md). Phase 5 remains deferred pending a new `go`.

Phase records describe implemented changes, not future capabilities. Detailed
file manifests and actual checks remain in the linked evidence reports.

## 0.3.0 — Phase 3, 2026-10-01

### Added
Vasicek, Hull–White, GBM and Heston process coefficients; supplied-shock exact/Euler
strategies and reported Heston projected Euler; analytical rate bonds/bond calls and
stable Fourier Heston European calls. Strict correlation PSD/Cholesky validation
and separate reported opt-in eigenvalue repair. Sourced immutable calibration
objectives, strict Pydantic ingestion and injected bounded SciPy fitting with
convergence/failure, residuals, RMSE, hashes, bounds and local uncertainty diagnostics.
Synthetic recovery examples and independent mathematical/domain/failure checks.

### Changed
Release/API/CLI/Compose metadata advances to 0.3.0/Phase 3; the deterministic-discounting
model remains 0.2.0. SciPy stubs are development-only. Every canonical ADR was reviewed;
0005 is accepted/implemented and 0008/0009 are new. Learning/architecture/workflow/
methodology/reproduction/limitations and phase ledger now describe actual code.

### Validation and limitations
[Phase 3 evidence and complete manifest](docs/validation/phase-3.md) records actual
checks and scoped Docker cleanup. Constant coefficients, explicit smooth Hull–White
curve, projected Heston boundary bias and local uncertainty assumptions apply.
No RNG/path engine, exposure, XVA, global optimizer or persisted calibration is added.
Final Windows/Python 3.13.2 and Linux/Python 3.12.14 runs each passed **483 tests**
with real isolated PostgreSQL, no skips and **99.01%** coverage. Lint/format/mypy,
pre-commit, documentation, wheel/sdist, container/readiness and scoped cleanup passed.

## Documentation maintenance between Phases 2 and 3, 2026-10-01

### Added
- Canonical `docs/decisions` register with seven individual ADRs and per-phase review
  history. Backfilled Phase 1/2 decisions without altering their original evidence.
- Contributor/agent rules, roadmap, onboarding/code/financial/operations guides,
  local documentation validation and ownership-checked Docker cleanup utility.

### Changed
- README navigation and learning path; legacy `docs/adr` records are historical.
- CI checks documentation and cleans only its named disposable Compose stack,
  including cleanup after failures. Hosted CI has not been executed locally.

### Scope
No quantitative calculation, package version or implementation phase changed.
Random-sequence and correlation ADRs explicitly distinguish future policies from
implemented metadata. See [maintenance evidence](docs/validation/documentation-maintenance.md).

## 0.2.0 — Phase 2, 2026-10-01

### Added
Immutable/source-labelled market snapshots and ingestion; discount/zero/projection
curves and bounded deposit/par-swap bootstrap; deterministic cash-flow/bond/swap/FX
pricing and central zero-knot/FX sensitivities. Input hashes, flow reconciliation,
synthetic replay and analytical/property/regression rejection checks were added.

### Validation and limitations
333 tests passed on Windows/Python 3.13.2 and Linux/Python 3.12.14, with real
PostgreSQL and 99.07% branch-inclusive coverage. Pricing is binary64 with unrounded
Decimal reporting; no stochastic simulation, exposure or XVA.
[Phase 2 files and evidence](docs/validation/phase-2.md).

## 0.1.0 — Phase 1, verified 2026-10-01

### Added
Typed src-layout foundation, Decimal Money, date/calendar/day-count/compounding
primitives, configuration and run metadata, safe logs, PostgreSQL connectivity,
operational API/CLI, packaging, quality checks and containers.

### Validation and limitations
141 tests passed with real PostgreSQL and 99.84% coverage. No pricing was implemented
in this phase. [Phase 1 files and evidence](docs/validation/phase-1.md).
