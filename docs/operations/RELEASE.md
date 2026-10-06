# Release and evidence checklist

Current release is 0.4.0 / Phase 4 complete. Phase boundaries are independent of documentation
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
Use `scripts/verify_phase4.ps1`; useful 0.4.0 and earlier release images remain.
The unchanged deterministic/calibration models retain versions 0.2.0/0.3.0.
