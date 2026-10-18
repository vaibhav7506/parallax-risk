# Parallax Risk decision register

This is the canonical register from the documentation maintenance update on
2026-10-01, updated through 2026-10-02. **12 of 12 implementation phases are complete.**
Release 0.12.0 completes the final Phase 12; no later phase is authorized.
Decision numbers identify decisions, not phases. Each decision retains a phase
history so reviews and changes can be counted without erasing earlier choices.

| ID | Decision | Status / implemented scope | Introduced in implementation |
|---|---|---|---|
| 0001 | [Clean architecture](0001-clean-architecture.md) | Accepted | Phase 1; extended Phases 2/5/6/7/8/9 |
| 0002 | [Money representation](0002-money-representation.md) | Accepted | Phase 1; pricing boundary Phase 2; portfolio use Phase 5 |
| 0003 | [Immutable market snapshots](0003-immutable-market-snapshots.md) | Accepted | Phase 2; conditional paths Phase 6 |
| 0004 | [Random sequence reproducibility](0004-random-sequence-reproducibility.md) | Accepted metadata and addressed pseudo/Sobol sequences | Phases 1–4 |
| 0005 | [Correlation validation](0005-correlation-validation.md) | Accepted | Phase 3 |
| 0006 | [Persistence boundaries](0006-persistence-boundaries.md) | Superseded by 0029; connectivity retained | Phase 1 |
| 0007 | [Deterministic curves and pricing](0007-deterministic-curves-and-pricing.md) | Accepted | Phase 2 |
| 0008 | [Stochastic models and discretization](0008-stochastic-models-and-discretization.md) | Accepted | Phase 3 |
| 0009 | [Bounded calibration and uncertainty](0009-bounded-calibration-and-uncertainty.md) | Accepted; numerical construction refined in Phase 9 | Phase 3; refinement Phase 9 |
| 0010 | [Independent sampling units and controls](0010-independent-sampling-units.md) | Accepted | Phase 4 |
| 0011 | [Batched paths and Gaussian covariance](0011-batched-paths-and-gaussian-covariance.md) | Accepted | Phase 4 |
| 0012 | [Legal portfolio snapshots](0012-legal-portfolio-snapshots.md) | Accepted | Phase 5 |
| 0013 | [Collateral ledger and margin policy](0013-collateral-ledger-and-margin-policy.md) | Accepted | Phase 5 |
| 0014 | [Conditional market paths](0014-conditional-market-paths.md) | Accepted | Phase 6 |
| 0015 | [Credit/default/dependence](0015-credit-default-dependence.md) | Accepted | Phase 6 |
| 0016 | [Exposure/cash/grid EAD](0016-exposure-statistics-and-cash-policy.md) | Accepted | Phase 6 |
| 0017 | [Unilateral credit adjustments](0017-unilateral-credit-adjustments.md) | Accepted; implemented and verified | Phase 7 |
| 0018 | [Additive funding/external IM](0018-additive-funding-and-external-margin.md) | Accepted; implemented and verified | Phase 7 |
| 0019 | [Common-stream risk/residual](0019-xva-common-stream-risk-attribution.md) | Accepted; implemented and verified | Phase 7 |
| 0020 | [Restricted standardized CCR](0020-restricted-standardized-ccr.md) | Accepted; implemented and verified | Phase 8 |
| 0021 | [Legal-unit IMM challenger](0021-legal-unit-imm-challenger.md) | Accepted; implemented and verified | Phase 8 |
| 0022 | [CCR capital comparison](0022-ccr-capital-comparison.md) | Accepted; implemented and verified | Phase 8 |
| 0023 | [Comparable model outputs and reproducible findings](0023-validation-comparability.md) | Accepted; implemented and verified | Phase 9 |
| 0024 | [Independent-unit convergence and uncertainty](0024-validation-inference.md) | Accepted; implemented and verified | Phase 9 |
| 0025 | [Sourced and ordered stress scenarios](0025-sourced-stress-scenarios.md) | Accepted; implemented and verified | Phase 9 |
| 0026 | [Controlled quantitative mutations](0026-controlled-quantitative-mutations.md) | Accepted; implemented and verified | Phase 10 |
| 0027 | [Bounded adversarial model search](0027-bounded-adversarial-search.md) | Accepted; implemented and verified | Phase 10 |
| 0028 | [Material-change forensic evidence](0028-material-change-forensics.md) | Accepted; implemented and verified | Phase 10 |
| 0029 | [Transactional governance persistence](0029-governance-persistence.md) | Accepted; implemented and verified | Phase 11 |
| 0030 | [Governed risk-run lineage](0030-governed-risk-lineage.md) | Accepted; implemented and verified | Phase 11 |
| 0031 | [Monitoring and alert transitions](0031-monitoring-alert-transitions.md) | Accepted; implemented and verified | Phase 11 |
| 0032 | [Evidence-only HTML/JSON reports](0032-evidence-report-rendering.md) | Accepted; implemented and verified | Phase 11 |
| 0033 | [Server-selected nominal financial wire schemas](0033-nominal-service-wire.md) | Accepted; implemented and verified | Phase 12 |
| 0034 | [Durable owned jobs and success-linked lineage](0034-durable-service-jobs.md) | Accepted; implemented and verified | Phase 12 |
| 0035 | [Explicit principal roles, safe transport and work admission](0035-service-authentication-and-limits.md) | Accepted; implemented and verified | Phase 12 |
| 0036 | [Preserve financial history with a cumulative validation pass](0036-cumulative-collateral-history.md) | Accepted; implemented and verified | Phase 12 |

There are **36 canonical ADRs**; 35 are accepted and ADR 0006 is superseded by 0029. The prior sequence proposal is now
implemented and reviewed; earlier history remains intact.

## Phase ledger

| Event | Release / state | Decision IDs with material implementation changes | Count | Actual verification evidence |
|---|---|---|---|---|
| Phase 1 | 0.1.0 COMPLETE | 0001, 0002, 0004, 0006 | 4 | [141 tests; foundation report](../validation/phase-1.md) |
| Phase 2 | 0.2.0 COMPLETE | 0001, 0002, 0003, 0004, 0007 | 5 | [333 tests; deterministic report](../validation/phase-2.md) |
| Documentation maintenance, 2026-10-01 | Phase remains 2 COMPLETE | Register reconstructed from actual code/history; 0005 recorded as user-requested proposal | 7 ADR files created/reviewed; **0 implementation phases advanced** | [Maintenance report](../validation/documentation-maintenance.md) |
| Phase 3 | 0.3.0 COMPLETE | 0001, 0004, 0005, 0008, 0009 | 5 material changes; all 9 ADRs reviewed | [483 tests on both platforms; model/calibration report](../validation/phase-3.md) |
| Phase 4 | 0.4.0 COMPLETE | 0001, 0004, 0005, 0008, 0010, 0011 | 6 material changes; all 11 ADRs reviewed | [653 tests on both platforms; Monte Carlo research report](../validation/phase-4.md) |
| Phase 5 | 0.5.0 COMPLETE | 0001, 0002, 0012, 0013 | 4 material changes; all 13 ADRs reviewed | [742 tests on both platforms; portfolio report](../validation/phase-5.md) |
| Phase 6 | 0.6.0 COMPLETE | 0001, 0003, 0014, 0015, 0016 | 5 material changes; all 16 ADRs reviewed | [821 tests on both platforms; exposure/credit report](../validation/phase-6.md) |
| Phase 7 | 0.7.0 COMPLETE | 0001, 0017, 0018, 0019 | 4 material changes; all 19 ADRs reviewed | [943 tests on both platforms; XVA/risk report](../validation/phase-7.md) |
| Phase 8 | 0.8.0 COMPLETE | 0001, 0020, 0021, 0022 | 4 material changes; all 22 ADRs reviewed | [1072 tests on both platforms; CCR prototype report](../validation/phase-8.md) |
| Phase 9 | 0.9.0 COMPLETE | 0001, 0009, 0023, 0024, 0025 | 5 material changes; all 25 ADRs reviewed | [1209 tests on both platforms; validation lab report](../validation/phase-9.md) |
| Phase 10 | 0.10.0 COMPLETE | 0001, 0026, 0027, 0028 | 4 material changes; all 28 ADRs reviewed | [1336 tests on both platforms; adversarial lab evidence](../validation/phase-10.md) |
| Phase 11 | 0.11.0 COMPLETE | 0001, 0006, 0029–0032 | 6 material changes; all 32 ADRs reviewed | [1462 tests on both platforms; governance/reporting evidence](../validation/phase-11.md) |
| Phase 12 | 0.12.0 COMPLETE | 0001, 0013, 0029, 0030, 0032, 0033–0036 | 9 material changes; all 36 ADRs reviewed | [1610 tests on each platform; final release evidence](../validation/phase-12.md) |

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
