# Documentation maintenance evidence — 2026-10-01

This is maintenance between implementation phases. **Phase 2 remains complete;
Phase 3 is NOT IMPLEMENTED and awaits `go`.** Release/financial formulas and the
historical phase reports are unchanged. The user supplied mandatory documentation
and project-scoped Docker retention/cleanup instructions.

## Documentation update

Created a canonical seven-ADR decision register, including the user's requested
five filenames. Every ADR records Phase 1, Phase 2 and this maintenance event;
nonapplicable/future functionality is labelled honestly. Register counts distinguish
decision changes, reviews and implementation phases. Earlier ADRs and original
phase evidence remain historical; the historical index maps old to canonical IDs.

Added agent/contributor/developer/security rules, roadmap/changelog, documentation
homepage, code/domain/workflow/reproduction/glossary/limitation guides, current
architecture/methodology/validation/testing/operations/API guides and a first-pricing
tutorial. Updated README navigation and the foundation architecture cross-reference.
Created documentation validation and scoped Docker cleanup utilities; CI now checks
docs and uses exact project teardown even after failures.

## Terminology, assumptions and limitations

Terminology links cover CCR/model risk, NPV, curves/fixings/bootstrap, signs/dirty PV,
PV01/DV01/FX delta, hashes/run metadata and clearly future sequence/correlation/model
concepts. No financial assumption or formula changed. Learning guides clarify
Decimal Money vs binary64 pricing, exact FX orientation/settlement, no known-fixing
fallback, conditional monotonicity and zero-knot sensitivity scope.

New operational policy: disposable verification containers/writable files and their
test network/volume are removed after results are preserved; useful release/rollback
images/shared cache/normal project data are retained. Ownership ambiguity prevents
cleanup. New tooling cannot certify external URL availability, security, financial
accuracy or future functionality. Existing quantitative limitations are consolidated,
not removed.

Architecture documentation changed: **yes**, navigation/ownership explanations;
application architecture behavior unchanged. Workflow documentation changed:
**yes**, explicit implemented call path and clearly planned future steps.

## Observed maintenance checks

The original **333 tests / 99.07% coverage** belongs to Phase 2 evidence; it is not
claimed as a newly executed full suite during this maintenance task.

| Check | Result |
|---|---|
| Docker baseline audit | No Parallax Risk containers/networks/volumes remained; release images 0.1.0/0.2.0 present |
| Cleanup preview | Exact Phase 2 verification project, no resources selected at baseline |
| Cleanup ownership guard | Controlled wrong-workspace fixture rejected before any mutation; correctly owned fixture remained |
| Cleanup apply | Controlled owned container, test network and disposable volume removed; all pre-existing container IDs retained |
| Local documentation/reference/index/ADR review checks | All 60 Markdown files reachable; seven canonical ADRs, completed-phase ledger/reviews, local links and 234 concrete path references validated |
| Documentation guard fixtures | Valid graph accepted; broken link, orphan, absent code reference, missing phase review and wrong ADR count rejected; temporary files removed |
| Changed documented commands and safe replay | CLI help/version/config/run-context executed and JSON validated; synthetic pricing demo executed with four computed results and labelled input |
| Code/class mapping | 20 principal documented class/function names verified against source ASTs |
| Cleanup attachment/use guards | Unowned network attachment and volume user rejected; controlled fixtures then removed |
| Cleanup phase/final inventory | Phase 13 rejected before Docker work; final Phase 2 cleanup selected zero resources; no Parallax Risk containers/networks/volumes left |
| Intermediate rebuild images | Three exact historical Phase 2 intermediate IDs inspected; already absent, so nothing removed |
| CI configuration | YAML parsed; docs gate, exact project commands and unconditional teardown verified |
| Ruff/mypy/format | Lint and formatting checks passed; strict production mypy passed in 46 source files; documentation utility passed separate strict mypy |
| Hosted CI | Updated configuration inspected; not executed here |

Only newly created Parallax Risk guard fixtures were removed. Current release and
useful rollback images remain. Other projects' containers/volumes/networks/images
and shared layers/cache are not pruned. The maintenance utilities add no database
or financial job logic.

## Inconsistencies corrected

- Existing `docs/adr` numbering is preserved as historical; `docs/decisions` is the
  canonical register with per-phase history and a mapping, rather than two competing indexes.
- Seed metadata is not described as an implemented random-sequence engine. Correlation
  requirements are a Proposed/NOT IMPLEMENTED record, not a fake validator/model page.
- CI previously selected by image ancestry and had no explicit finally teardown.
  It now targets `parallax-risk-ci` with an `if: always()` cleanup step.
- Completed phases, future work, exact Money versus valuation precision and operational
  versus financial API scope are explicit throughout onboarding/reference pages.

## Deferred documentation

Detailed stochastic models/calibration, Monte Carlo, collateral/exposure/credit/XVA,
capital, challenger/convergence/stress/uncertainty/mutation/adversarial/governance,
performance and future tutorials wait for their actual authorized implementations.
No empty documents or future code directories were created.

## File manifest

The full created/updated file list follows. Source modules,
release version and historical ADR/phase-report contents were not modified.

### Created (51 files)

- `AGENTS.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `DEVELOPMENT.md`
- `ROADMAP.md`
- `SECURITY.md`
- `docs/CODEBASE_GUIDE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/GLOSSARY.md`
- `docs/INDEX.md`
- `docs/LIMITATIONS.md`
- `docs/REPRODUCIBILITY.md`
- `docs/WORKFLOW.md`
- `docs/adr/README.md`
- `docs/api/ENDPOINTS.md`
- `docs/api/ERRORS.md`
- `docs/api/EXAMPLES.md`
- `docs/api/OVERVIEW.md`
- `docs/architecture/COMPONENTS.md`
- `docs/architecture/DATA_FLOW.md`
- `docs/architecture/DEPENDENCY_RULES.md`
- `docs/architecture/DEPLOYMENT.md`
- `docs/architecture/OVERVIEW.md`
- `docs/decisions/0001-clean-architecture.md`
- `docs/decisions/0002-money-representation.md`
- `docs/decisions/0003-immutable-market-snapshots.md`
- `docs/decisions/0004-random-sequence-reproducibility.md`
- `docs/decisions/0005-correlation-validation.md`
- `docs/decisions/0006-persistence-boundaries.md`
- `docs/decisions/0007-deterministic-curves-and-pricing.md`
- `docs/decisions/README.md`
- `docs/methodology/CURVES.md`
- `docs/methodology/INDEX.md`
- `docs/methodology/MARKET_DATA.md`
- `docs/methodology/PRICING.md`
- `docs/operations/CONFIGURATION.md`
- `docs/operations/DATABASE.md`
- `docs/operations/DOCKER.md`
- `docs/operations/LOCAL_SETUP.md`
- `docs/operations/OBSERVABILITY.md`
- `docs/operations/RELEASE.md`
- `docs/operations/TROUBLESHOOTING.md`
- `docs/testing/STRATEGY.md`
- `docs/tutorials/01-FIRST-PRICING-RUN.md`
- `docs/validation/BENCHMARKING.md`
- `docs/validation/OVERVIEW.md`
- `docs/validation/SENSITIVITY.md`
- `docs/validation/documentation-maintenance.md`
- `docs/workflows/PRICING_WORKFLOW.md`
- `scripts/check_docs.py`
- `scripts/cleanup_docker.ps1`

### Updated (3 files)

- `.github/workflows/ci.yml`
- `README.md`
- `docs/architecture/foundation.md`
