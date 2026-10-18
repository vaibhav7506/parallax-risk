# Governance workflow

1. Explicitly select an isolated PostgreSQL database, own/dispose its SQLAlchemy
   engine, and upgrade via the packaged Alembic migration composition.
2. Inject PostgresGovernance into Governance; register development inventory and
   an immutable model Version. Retain actual source/configuration/parameter inputs.
3. Create owned Findings/Limitations from retained numerical evidence. Record a
   separate explicit decision with authority/rationale/evidence and any conditions.
4. Run GovernedXva with the real existing exposure/XVA engines, registered version,
   actor, UTC audit time, and explicit optional revision/calibration references.
5. Register immutable monitoring Policies; store comparable measured Evaluations.
   Create/acknowledge alerts, then resolve only using later recovery evidence.
6. Build the seven report kinds from actual results/snapshots and retain HTML/JSON.

Each write advances one revision. A stale revision/reference fails; reload and
review the change before attempting a new write. There is no blind retry or
transaction spanning an entire multi-record demonstration; earlier successful
records remain if a later write fails. Every individual snapshot/event write is
atomic. GovernanceRepository is a low-level persistence port; use Governance to
apply lifecycle/scope validation. Actor/authority values are declared metadata,
not authenticated identities or cryptographic signatures.

`src/parallax_risk/application/governance_examples.py` demonstrates actual Phase 9
validation and Phase 10 mutation evidence plus a governed XVA run with synthetic
inputs. Its fixed IDs intentionally reject a second execution in the same schema.
The weak-suite report retains misses; the conditional research decision does not
close its finding. Outputs are research evidence, not production approval.

The steps above are the direct Phase 11 library workflow. Release 0.12.0 additionally
authenticates service principals and applies roles to governance writes; actor and
approval authority must match the authenticated subject.
[HTTP/CLI workflow](../api/EXAMPLES.md) and [service contracts](../methodology/SERVICE.md).
[First run](../tutorials/10-FIRST-GOVERNANCE-RUN.md),
[contracts and limits](../methodology/GOVERNANCE.md),
[database lifecycle](../operations/DATABASE.md).
