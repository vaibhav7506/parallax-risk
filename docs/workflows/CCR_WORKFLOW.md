# CCR prototype workflow

`CcrService` in `src/parallax_risk/application/ccr.py` injects the production
ExposureService/PortfolioService composition. Quantitative formulas remain in
`src/parallax_risk/domain/ccr/`; no API handler, database adapter, import-time
setting or global RNG implements them.

1. Supply a validated SimulationRequest, PortfolioSnapshot, matching
   ConditionalMarketScenario and RunContext with the same seed/date origin.
2. Supply version/source-labelled SupervisoryParameters and ComparisonPolicy
   in book currency. Every legal set must use that reporting currency.
3. Supply exactly one ledger and ScopeMargin per CSA. Explicit TH/MTA must equal
   actual CSA policy; MPOR/NICA are separate caller assumptions. Daily receive-capable
   CSA is required, plus the existing exposure restrictions. Unknown/duplicate
   scopes reject, as do missing or unsupported contracts.
4. Validate/price the complete origin book and then separate legal units. Each
   enforceable set is one unit; each non-enforceable active trade is its own unit.
   An empty/fully inactive scope rejects. Obtain origin markets from addressed
   deterministic replay; map only vanilla domestic IRS/domestic-quote FX forwards.
5. Calculate standardized terms and actual exposure paths with scoped ledgers.
   Check returned book/run/market/account evidence. Calculate challenger EE/EPE
   through the exact first-year/final-payment node; reject missing horizon nodes.
6. Compare unit EAD/capital inputs, exceptions and component bridges. Aggregate
   EADs by addition, without cross-scope offsets. Retain all input/path hashes.

`maximum_output_bytes` is a per-unit exposure output budget. Units replay serially;
the result retains summarized evidence rather than all positive/negative path
arrays. Source parameters/configurations have to be retained with the report to
resolve their hashes later. No persisted result repository is claimed.

```sh
python scripts/demo_ccr.py
python -m pytest tests/unit/test_ccr_contracts.py tests/quantitative/test_ccr.py tests/integration/test_ccr_workflow.py -q --no-cov
```

The focused command deliberately omits full-project coverage; the required full
phase suite is `python -m pytest` with live isolated PostgreSQL. Do not report a
focused run or a skipped database case as full verification.

[Tutorial](../tutorials/07-FIRST-CCR-COMPARISON.md),
[standardized](../methodology/STANDARDIZED_CCR.md),
[challenger](../methodology/IMM_CHALLENGER.md),
[comparison](../methodology/CCR_COMPARISON.md), [Phase 8 evidence](../validation/phase-8.md).

Phase 8 mapping rejects scheduled future termination/reset contracts. The
explicit MPOR must meet the configured business-day floor. The application
checks simulation-request metadata, dates, profile units/path count and path shape
in addition to book/run/market/account evidence; each scope retains runtime
simulation metadata for replay.
