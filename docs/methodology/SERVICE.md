# Authenticated service contracts

Phase 12, release 0.12.0. Numerical engines and their financial assumptions remain
those of Phases 2–11. [API](../api/ENDPOINTS.md), [deployment](../operations/SERVICE.md),
[decisions](../decisions/README.md) and [verification](../validation/phase-12.md).

## Boundaries and representation

`src/parallax_risk/application/workflows.py` selects 16 immutable command types and
calls injected engines. Routers perform transport composition only. Pydantic forbids
extra envelope fields and validates declared strict integers/booleans/strings.
`src/parallax_risk/application/wire.py` decodes only a server-selected nominal type;
`__type__` is an exact discriminator, never an import instruction. Money uses finite
Decimal text; model/pricing numbers use finite binary64. Civil dates use ISO dates;
instants normalize to aware UTC. Arrays use validated shape plus base64 bytes.
No pickle, eval, client-selected module loading or server-side client file path exists.
The credit-policy protocol has an explicit ReducedFormSpread concrete allowlist.

`GET /v1/workflows` returns draft-2020-12 schemas generated from those same selected
annotations. OpenAPI documents Pydantic envelopes, authentication and routes; nested
nominal command schemas live in this companion endpoint. Economic constructors then
check currency, units, dates, horizons and model domains. Numeric JSON integers may
represent a binary64 field; integer/boolean fields never accept boolean/numeric text
coercion. JSON rejects duplicate keys, NaN/Inf, overflow and excessive structure.

## Retention, jobs and replay

Before submission, register the exact owned portfolio, market snapshots and conditional
scenarios embedded in the command. Registration is immutable and compares canonical
content digests. Natural keys are portfolio_id:version, snapshot_id:version and scenario
hash. Counterparty/netting/CSA/pricing-context objects may also be retained separately;
calculations use the complete explicit command rather than constructing a book from
unspecified object IDs.

A queued job stores its owner, exact request, operation, registered model/version,
original correlation ID and UTC timestamps. Owner + Idempotency-Key uniquely identifies
a submission: identical operation/model/version/request returns the original job;
changed input returns 409. A new correlation ID does not replace the original one.
Admission is globally serialized in PostgreSQL and includes running jobs.

Local workers claim queued rows using FOR UPDATE SKIP LOCKED and a claim token.
The guarded state machine is queued → running → succeeded/failed; operator abandonment
also permits queued/running → failed. Inputs and terminal states are immutable.
Success requires a committed lineage foreign key. Computation commits lineage before
completion in a separate transaction; it is not an atomic two-record commit. An uncertain
persistence failure halts that worker, leaves the claim visible and makes readiness fail.
It never automatically retries. Inspect evidence, then explicitly abandon an owned
uncertain job and use a fresh idempotency key if a replay is appropriate. Abandonment
cannot interrupt numerical code; a late finish fails its claim/state comparison.
Shutdown waits for active admitted computations. There is no hard wall-time cancellation,
automatic restart recovery, distributed worker implementation or Redis dependency.

Every successful service job records actual result/request digests, registered model
version, portfolio/market/CSA fingerprints, market and credit stream addresses, UTC
submission time and actual runtime. Missing source commit remains null; the repository
has no authenticated commit to infer. Absence of a portfolio/market is explicitly
fingerprinted; multiple input hashes are listed and aggregated. Retained input/result
bytes accompany those digests. Low-level library calls remain ungoverned experiments.

An optional calibration_job must be an owned successful, converged Vasicek bond
calibration whose fitted tuple appears exactly in submitted Vasicek processes. Other
model calibration runs can be executed and inspected; linked deployment is rejected
until an explicit model-specific parameter mapping is supported. The reference does
not prove that every process/currency was calibrated. The synthetic demo deliberately
shares fitted rate parameters across two synthetic currencies.

## Access, limits and reporting

Opaque high-entropy API keys authenticate through an injected port. The supplied adapter
compares SHA-256 digests in constant time and stores no raw key. This is local static-key
authentication, not enterprise identity, signed approval or regulatory certification.

| Role | Permitted action |
|---|---|
| reader | Owned inputs/jobs/reports; shared governance inventory/history queries |
| analyst | Ingestion, calculations, reports; also supply reader for subsequent retrieval |
| validator | Inventory/version/findings/limitations/monitoring writes |
| approver | Decisions and active-model transitions; approval authority must match subject |
| operator | Abandon an owned pending job; also needs reader to inspect it |

Roles are explicit and do not implicitly include other roles. Governance is a shared
research inventory; financial job/object/report reads are owner-scoped. Clients cannot
write computed lineage. Governance decisions still preserve open findings and existing
research state rules; an authenticated recorded decision is not institutional approval.

Default limits: 1 MiB request bytes (configurable 1 KiB–4 MiB), 100,000 JSON nodes,
depth 48, 120 requests/minute/principal, 256 active principals, 64 globally pending jobs,
1 local worker (1–4 configurable), 16,384 paths, 2,000 trades, 512 steps, 16 driver/state
dimensions and a 2,000,000 work-unit budget. Work counts path×time×trade×evaluations plus
collateral history scans. Search ≤64 evaluations; stress/convergence ≤16 cases;
mutation ≤32 faults; bootstrap 2–1000 replicates; calibration ≤1000 evaluations/64 quotes
with a quadrature budget. The 64 MiB retained result/output/batch estimate is not an RSS
or hard latency guarantee. A submitted daily capital margin grid can therefore be
accepted at small path counts while a costly larger run is rejected explicitly.

Pages use exclusive lexicographic after + limit (1–100), returning brief records without
loading full job results. Use the last key/job_id as the next cursor; concurrent inserts
before that key require a new listing. No snapshot-consistent page guarantee is claimed.

Seven JSON/HTML report kinds read only retained successful compatible jobs or registered
governance records. Computed report synthetic status comes from the job; governance
summaries require an explicit declaration. Interpretation is caller text, escaped in
HTML and never an inferred pass decision. HTML uses restrictive CSP and no scripts or
external assets. JSON embeds report metadata under `report`. Synthetic flags on sample
sources cannot be downgraded. Declared flags cannot authenticate external market data.

The error representation follows [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html)
with about:blank, HTTP status, fixed detail code, instance and correlation_id. Logs expose
only event/status/error class/correlation; payloads, raw secrets and URLs are omitted.
