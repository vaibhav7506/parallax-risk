# Release and evidence checklist

Current release is 0.10.0 / Phase 10 complete. Phase boundaries are independent of documentation
maintenance, which does not authorize new quantitative functionality.

1. Complete only the authorized phase, inspect changes and run applicable numerical/
   rejection/integration checks with real isolated PostgreSQL where required.
2. Run lint/format, strict mypy, docs checker, packaging and container checks applicable
   to changed code. Record actual versions/counts/coverage/image IDs and warnings.
3. Synchronize package/build/API/CLI/Compose versions when a release changes. No
   fabricated source commit or hosted-CI result is permitted.
4. Review every canonical ADR, append a phase-history row, update the ledger/counts,
   changelog/roadmap/agent state and affected code/methodology/workflow/limits guides.
5. Preserve existing historical phase reports, create the new file manifest/evidence
   and list anything not implemented/deferred. Validate local links and actual commands.
6. Save useful outputs, remove only disposable test resources in finally, and report
   retained release/rollback images/data. Keep shared layers/cache; never global-prune.
7. Report documentation changes and stop, awaiting `go` for the next phase.

No publishing/deployment to external infrastructure, automatic model approval or
production hardening is implied by building a local wheel/image.

For Phase 4 preserve executed notebooks, replayable demo JSON, measured benchmark
JSON, dependency locks, actual Windows/Linux PostgreSQL tests and scoped cleanup logs.
Use `scripts/verify_phase10.ps1` for the active release; useful 0.10.0/0.9.0/0.8.0/0.7.0 and earlier release
images remain. The Phase 4 helper is historical evidence, not a current version check.
The unchanged deterministic/calibration models retain versions 0.2.0/0.3.0.

For Phase 5 preserve synthetic portfolio JSON replay, full pricer/book/market/ledger
lineage, new exact-policy/FX/lifecycle/MPOR checks and actual platform/PG/cleanup logs.
No notebook/math-model/dependency change is required; simulation stays engine 0.4.0.
See [Phase 5 evidence](../validation/phase-5.md).

Phase 6 retains full synthetic input/replay JSON, conditional market digest and
profile/credit method labels, plus live PostgreSQL tests and exact release image IDs.
Every canonical ADR gets a Phase 6 review; new IDs 0014–0016 declare additional policies.
[Phase 6 evidence](../validation/phase-6.md) records actual results and retained/removed resources.

Phase 7 preserves full synthetic XVA inputs/results, five revaluations, actual
stability and ordered residual evidence. Review every canonical ADR; new IDs
0017–0019 define credit, funding/IM and risk policies. Retain needed release/rollback
images and logs, and record exact project cleanup and unchanged unrelated workloads.
[Phase 7 report](../validation/phase-7.md) records actual checks and file hashes.

Phase 8 preserves legal-unit simulation/request/book/account/configuration/path
fingerprints, supported-contract/formula assumptions and honest exception/capital
labels. Record actual full Windows/installed-wheel Linux tests, live PostgreSQL,
demo replay, final wheel/source hashes and phase8-verification cleanup. Existing
.2/.3/.4/.7 model versions and historical results remain unchanged.
[Phase 8 report](../validation/phase-8.md).

## Phase 9 lab scope

Phase 9 verification uses `scripts/verify_phase9.ps1`; retain useful 0.8.0 rollback/evidence images and needed result artifacts. Only exact labelled parallax-risk-phase9-verification resources are removed in finally. Completion counts must come from the new actual runs, not the earlier 1072-test record.
[Lab methods](../methodology/MODEL_VALIDATION.md), [phase evidence](../validation/phase-9.md).

## Phase 10 release verification

Use `scripts/verify_phase10.ps1` for the active 0.10.0 scope. It checks operational
HTTP/CLI/live PostgreSQL and full Windows plus installed-wheel Linux tests; always
performs exact Phase 10 ownership cleanup. Save actual results and production source
hashes while the verification image is running. Retain rollback images and historical
evidence. Never relabel the Phase 9 1209-test result as a newly executed run.
[Actual report](../validation/phase-10.md).
