# ADR 0003 — Immutable market snapshots

**Status:** Accepted. **Recorded:** 2026-10-01; implemented in Phase 2.

## Context
A price must identify the exact observations, conventions and provenance used.
Mutable input dictionaries can change after validation and invalidate that evidence.

## Decision
Ingest with frozen extra-forbidden Pydantic boundaries; convert to independently
frozen domain values/tuples. Canonically order currencies and observations and hash
identity/version, values, conventions and source metadata with schema-1 SHA-256 JSON.
Reject duplicates, invalid dates/currencies and malformed/nonfinite values. Required
fixings and direct FX quotes have no inferred fallback.

## Alternatives considered
Mutable vendor payloads reduce conversion work but allow accidental edits.
Database IDs alone identify rows but do not prove input content. Content-only hashes
without source/version omit part of the evidence.

## Why this decision
Immutable content identity makes input changes visible and enables deterministic
replay independently of persistence availability.

## Consequences
Updates create new versions; sensitivity shocks do not mutate the base snapshot.
Daily cutoff and strict date/instant ingestion are explicit. Derived curves are
separate immutable inputs, not automatically inferred from observation categories.

## Risks
Hashes are not signatures or authenticity checks. A valid snapshot can still be
stale or synthetic; there is no source-specific intraday/freshness policy.

## Follow-up
Source integrations, authenticated lineage and persisted versions remain DEFERRED.

## Related code
`src/parallax_risk/domain/market/snapshot.py` (`MarketSnapshot`),
`src/parallax_risk/domain/market/observations.py` (`SourceMetadata`),
`src/parallax_risk/application/market_data.py` (`MarketSnapshotInput`),
`src/parallax_risk/common/canonical.py` (`content_hash`),
`tests/unit/test_market_snapshots.py`.

## Phase history

| Phase | Change / review | Evidence |
|---|---|---|
| 1 | Not applicable: market snapshots NOT IMPLEMENTED | [Phase 1](../validation/phase-1.md) |
| 2 | Frozen/source-labelled snapshot, ingestion/version/hash and failure checks introduced | [Phase 2](../validation/phase-2.md) |
| Maintenance 2026-10-01 | Dedicated canonical ADR created; snapshot behavior unchanged | [Register](README.md) |
| 3 | Reviewed; no snapshot change; sourced calibration premiums are separate immutable objective inputs | [Phase 3](../validation/phase-3.md) |
