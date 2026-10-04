# Parallax Risk decision register

This is the canonical register from the documentation maintenance update on
2026-10-01. **3 of 12 implementation phases are complete.** Phase 4 awaits `go`.
Decision numbers identify decisions, not phases. Each decision retains a phase
history so reviews and changes can be counted without erasing earlier choices.

| ID | Decision | Status / implemented scope | Introduced in implementation |
|---|---|---|---|
| 0001 | [Clean architecture](0001-clean-architecture.md) | Accepted | Phase 1; extended Phase 2 |
| 0002 | [Money representation](0002-money-representation.md) | Accepted | Phase 1; pricing boundary Phase 2 |
| 0003 | [Immutable market snapshots](0003-immutable-market-snapshots.md) | Accepted | Phase 2 |
| 0004 | [Random sequence reproducibility](0004-random-sequence-reproducibility.md) | Accepted envelope; sequence policy Proposed / NOT IMPLEMENTED | Phase 1 envelope; Phase 2 input hashes |
| 0005 | [Correlation validation](0005-correlation-validation.md) | Accepted | Phase 3 |
| 0006 | [Persistence boundaries](0006-persistence-boundaries.md) | Accepted | Phase 1 |
| 0007 | [Deterministic curves and pricing](0007-deterministic-curves-and-pricing.md) | Accepted | Phase 2 |
| 0008 | [Stochastic models and discretization](0008-stochastic-models-and-discretization.md) | Accepted | Phase 3 |
| 0009 | [Bounded calibration and uncertainty](0009-bounded-calibration-and-uncertainty.md) | Accepted | Phase 3 |

There are **9 canonical ADRs**: 8 fully accepted and 1 mixed accepted/proposed.
Proposed random-sequence policy is not a claim of implemented code or tests.

## Phase ledger

| Event | Release / state | Decision IDs with material implementation changes | Count | Actual verification evidence |
|---|---|---|---|---|
| Phase 1 | 0.1.0 COMPLETE | 0001, 0002, 0004, 0006 | 4 | [141 tests; foundation report](../validation/phase-1.md) |
| Phase 2 | 0.2.0 COMPLETE | 0001, 0002, 0003, 0004, 0007 | 5 | [333 tests; deterministic report](../validation/phase-2.md) |
| Documentation maintenance, 2026-10-01 | Phase remains 2 COMPLETE | Register reconstructed from actual code/history; 0005 recorded as user-requested proposal | 7 ADR files created/reviewed; **0 implementation phases advanced** | [Maintenance report](../validation/documentation-maintenance.md) |
| Phase 3 | 0.3.0 COMPLETE | 0001, 0004, 0005, 0008, 0009 | 5 material changes; all 9 ADRs reviewed | [483 tests on both platforms; model/calibration report](../validation/phase-3.md) |

These counts are material decision changes, not file-edit or commit counts.
Historical phase numbers/test outcomes come from the original reports; retrospective
canonical numbering does not imply these filenames existed during those phases.

## How to maintain this register after every phase

Review every ADR, append the phase/date/change/evidence row, and update this ledger.
Write "reviewed; no change" for unchanged implemented decisions. Keep a proposal
label until implementation and verification exist. Record new IDs and counts;
never recycle numbers. Preserve old decisions and mark a replaced decision
superseded with a link to its successor. Update [CHANGELOG](../../CHANGELOG.md)
and the corresponding phase report/file manifest in the same phase.

## Historical records

The earlier [`docs/adr` records](../adr/README.md) remain unchanged historical
evidence. Their numbering was different: historical 0001/0002 map to canonical
0001; historical 0003 maps to canonical 0006; historical 0004 to canonical 0004;
historical 0005 to canonical 0007. The new register splits Money and snapshot
decisions for easier learning and phase tracking.
