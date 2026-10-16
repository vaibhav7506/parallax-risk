# Governance, lineage, monitoring and report contracts

Phase 11 implements a research governance layer. It records declared owners,
review schedules, decisions and evidence; it does not authenticate actors, certify
models, implement regulatory approval or infer conclusions from an LLM.

`src/parallax_risk/domain/governance/contracts.py` defines immutable Model, Version,
Finding, Approval, Limitation and Lineage. Model inventory includes type, owner,
purpose, status, version identifier, methodology, limitations, materiality,
validation frequency in civil days, last validation and next review. Review dates
are explicit caller policy; no calendar scheduler changes them automatically.
Model state advances development → validation → active → retired. Activation
requires a registered version of that model; recording an Approval does not
activate it or close findings. Same-state inventory edits retain audit history.

Versions retain configuration, parameter-set JSON and an explicit code reference.
They cannot be overwritten. Findings retain severity, original evidence, owner,
due date and description: open → remediating requires remediation text;
remediating → closed also requires closure evidence. Reopening, skipping states
or rewriting opening evidence fails. Phase 9 numerical Findings remain distinct
immutable check results; an owned governance Finding is created explicitly.
Conditional approval requires conditions; approval/rejection forbid conditions.
Authority, rationale, evidence and decision time are retained as declared metadata.
Limitations identify affected portfolio hashes, materiality and compensating controls.

Evidence Document is canonical JSON object text. Duplicate keys, unsupported
roots and nonfinite values fail. Read access returns a fresh object. Parsed JSON
arrays are frozen before the existing strict canonicalizer is invoked. Digests are
content fingerprints, not signatures. Retain original inputs alongside hashes.

## Transactions and history

`src/parallax_risk/application/governance.py` injects GovernanceRepository.
Each save checks the expected revision, locks observed parent/policy/evaluation
references in a consistent order and atomically advances the head plus appends
an audit event. Stale writes/references fail; callers must reread and reconsider.
`src/parallax_risk/infrastructure/persistence/governance.py` implements SQLAlchemy
PostgreSQL persistence. Schema revision 0011 is frozen under packaged Alembic
migration scripts. Events cannot be updated/deleted by ordinary SQL; immutable
kinds cannot advance their head. Deferred foreign keys prevent orphan heads.
Application constructors and workflows validate economic scope and transitions;
raw database administration is outside this trust boundary. No append-only claim
protects against a database administrator disabling constraints/triggers.

The original SELECT 1 readiness probe remains a connectivity check. It does not
prove revision 0011 exists. Migrations run explicitly, never during import/startup.
See [database operation](../operations/DATABASE.md) and
[ADR 0029](../decisions/0029-governance-persistence.md).

## Risk-run lineage

`src/parallax_risk/application/governed_risk.py` runs actual exposure and XVA through
injected existing engines. A returned GovernedRun always has committed immutable
lineage. Duplicate run IDs fail; persistence failure prevents a governed success
return. Lower-level pricing, calibration, simulation, CCR and validation library
experiments remain ungoverned numerical research entry points, not registered risk
runs. There is no HTTP job runner or automatic interception of arbitrary calls.

Lineage retains run/model/version IDs, optional caller source revision, actual book
and conditional-market hashes, full experiment configuration hash, optional
calibration ID, market seed and sequence plus credit threshold/rank addresses,
CSA content-version hashes, UTC run time, real simulation environment metadata,
run context/settings hash, market-path digest, initial-ledger hashes and result hash.
The configuration fingerprint includes request/book/markets/accounts/credit/own
credit/discount/funding/IM; run identity/time are excluded. Funding/credit inputs
are thus retained in configuration identity even though market hash names only
conditional markets. Calibration ID is an external reference, not a result store.
Missing revision/calibration remain null with explicit assumptions. Recorded code
reference and version label are caller declarations; no commit is invented.

## Monitoring

`src/parallax_risk/domain/governance/monitoring.py` supports parameter drift,
calibration-error drift, output drift, PFE movement, CVA movement, convergence
and validation-rule failures. Each immutable Policy declares metric, units, statistic, nonnegative threshold,
severity and rationale; observations declare their comparison-scope hash.
Observations retain finite values, evidence hashes and aware UTC timestamps.
Current must be later than baseline, and exact metric/unit/scope must agree.
Evidence providers supply actual measurements; there is no scheduled collector.

Statistics are abs(current-baseline), current-baseline, baseline-current or
current level. A breach is strictly statistic > threshold; equality is within
policy, with no hidden epsilon, relative normalization or zero-denominator fallback.
CVA remains signed (negative cost in the existing engine); choose increase/decrease
according to the declared question. Currency-valued thresholds use currency units;
parameters/errors/convergence preserve their own supplied units. Failure counts
must be nonnegative integers, unit count, statistic level. PFE policy must declare
its quantile/horizon/sampling comparison scope in the scope fingerprint.

Alerts require an actual breached stored Evaluation with matching model/version/
severity. Open → acknowledged → resolved; resolution needs a later comparable,
nonbreached Evaluation of the same immutable policy. Opening evidence cannot
change. A subsequent breach creates a new alert; no implicit reopen, external
notification delivery, incident scheduler or automatic remediation exists.

## Reports

`src/parallax_risk/application/governance_reports.py` emits technical validation,
governance summary, model comparison, stress, convergence, mutation and lineage
reports as HTML plus schema-1 JSON. Each consumes declared computed result types,
retains source assumptions/failures/residuals/misses, evidence digest, UTC generation
time, synthetic flag and explicitly caller-authored interpretation. JSON contains
canonical nominal dataclass metadata and nested evidence JSON text; consumers
parse that text as JSON. HTML escapes all stored strings, supplies a restrictive
CSP and contains no scripts, external assets or executable evidence links.
No PDF or LLM dependency is introduced. Rendering is deterministic for identical
records/metadata, not a promise of cross-platform numerical bytes.

Primary implementation references: [Alembic connection-sharing cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
and [PostgreSQL row locks](https://www.postgresql.org/docs/17/explicit-locking.html).
These explain transaction mechanics, not governance or financial validity.

[Workflow](../workflows/GOVERNANCE_WORKFLOW.md), [phase evidence](../validation/phase-11.md).
