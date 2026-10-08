# Market data and snapshot identity

## Intuition
A valuation must preserve what was known and where it came from. A market snapshot
contains observations, not automatically constructed models or a vendor authenticity guarantee.

## Implementation
`src/parallax_risk/domain/market/observations.py` defines Quote, RateObservation,
FxSpot, VolatilityObservation, CreditSpreadObservation, RateFixing and SourceMetadata.
`MarketSnapshot` validates daily date/currency/key consistency and canonical ordering.
`src/parallax_risk/application/market_data.py` (`MarketSnapshotInput`) rejects extra
fields, malformed numeric values and implicit epoch date/time coercion before domain conversion.

Content identity is `SHA256(canonical_schema_1_JSON(snapshot))`; the payload includes
identity/version, source/sample status, observations and declared conventions. A hash
detects input-content changes but proves neither authenticity nor economic correctness.
The hashing function is `src/parallax_risk/common/canonical.py` (`content_hash`).

## Assumptions, failure and validation
Rates/spreads are decimal annual units; FX is direct QUOTE/BASE for an explicit
settlement date. Source dates use the declared daily UTC cutoff. Known fixing dates
cannot be future. Optional categories may be empty; required lookups fail explicitly.
Duplicates, absent currencies, invalid maturity/expiry, nonpositive FX or nonfinite
data are rejected. No inverse/cross quote or projected historical fixing is synthesized.

`tests/unit/test_market_snapshots.py` covers nested immutability, mutation isolation,
hash replay/version changes and malformed inputs. The labelled fixture is
`data/sample/phase2_market.json`; no observed market data or fitted model is claimed
for that snapshot workflow. Phase 3 uses separate sourced option premium objectives
for [Heston calibration](CALIBRATION.md); raw volatility quotes are not substituted
for premiums. Intraday/source-specific freshness policy is absent.
See [full assumptions](deterministic-pricing.md) and [ADR 0003](../decisions/0003-immutable-market-snapshots.md).

Phase 6 [conditional market paths](EXPOSURE.md) construct model-derived snapshots
with synthetic/source labels. Generated fixings are held fixed after their fixing date;
origin observations remain caller supplied. These derived values do not imply authentic
market observations or vendor ingestion. Original immutable identity conventions remain.
