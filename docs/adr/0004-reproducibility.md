# ADR-0004: Explicit run context and canonical nonsecret configuration hash

**Status:** Accepted
**Date:** 2026-09-30
**Deciders:** Parallax Risk implementation (institutional review pending)

## Context
Future risk results need stable seeds, effective configuration and run correlation.
Identity, wall-clock time and environment defaults must not silently drive models.

## Decision
RunContext freezes RiskRunId, aware UTC timestamp, uint64 seed and SHA-256 digest.
Settings are validated at invocation. Hash canonical versioned JSON with sorted
keys, compact separators and finite values. Exclude credentials, recording database
presence. Inject ID/time for envelope replay; seed remains independent of both.
Logs carry run IDs without raw portfolio/configuration values. Lock dependencies.

## Options considered
| Option | Complexity | Cost | Scalability | Familiarity |
|---|---|---|---|---|
| Explicit immutable envelope | Moderate | Low | Serializable across compute boundaries | Standard provenance pattern |
| Seed only | Low | Incomplete replay evidence | Simple | Familiar numerical shortcut |
| Global RNG/config singletons | Low initial | Cross-run coupling | Unsafe concurrent reuse | Common prototype approach |

## Trade-off analysis
The envelope is deterministic when all fields are injected; a newly created run
has a fresh ID and current timestamp. Nonsecret configuration hashing avoids
credential disclosure but cannot uniquely identify connection credentials. Those
are operational dependencies, not quantitative model inputs.

## Consequences
This is foundation metadata, not complete model/portfolio/market lineage or a
simulation engine. Future phases add model version, calibration, sequence, source
revision and environment metadata. No random-stream logic is pre-built now.

## Action items
1. [x] Test hash ordering, secret exclusion, changes and envelope replay.
2. [x] Document seed range, hash schema and incomplete lineage limitations.
