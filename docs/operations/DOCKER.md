# Docker verification cleanup and retention

The user authorizes cleanup after testing **only for Parallax Risk**. Container
writable files disappear with removal of the disposable test container. Preserve
needed reports/artifacts first; do not delete arbitrary files inside a useful image
or service. Normal project database data must remain.

| Resource | Policy and ownership evidence |
|---|---|
| Phase verification containers | Remove after session, including failure; exact `parallax-risk-phaseN-verification` Compose project plus matching workspace or explicit verification labels |
| Standalone test container | Use `--rm`; identify project/purpose/workspace explicitly, retain required outputs outside writable layer |
| Test network/volume | Remove only exact verification-project labels, known `default`/`postgres_data` roles and no unowned attachments/users |
| Release images | Keep current `parallax-risk:0.10.0` and useful `0.9.0`/`0.8.0`/`0.7.0`/`0.6.0`/`0.5.0`/`0.4.0`/`0.3.0`/`0.2.0`/`0.1.0` rollback/evidence images |
| Normal Compose data/services | Retain; project `parallax-risk` is not a disposable phase verification project |
| Shared base images/layers/build cache | Retain; ownership is not exclusive, future builds can reuse them |
| Other projects or ambiguous resources | Retain; never use global prune or force removal |

## Preview and scoped teardown

PowerShell from the repository root:

```powershell
.\scripts\cleanup_docker.ps1 -Phase 10
.\scripts\cleanup_docker.ps1 -Phase 10 -Apply
```

Without `-Apply` the script inventories ownership-checked candidates only. It accepts
phases 1–12 and constructs the exact test project name; it has no arbitrary project
or filesystem-delete parameter. It inspects **all candidates before deleting any**,
rejects a mismatched workspace or unowned network/volume user, stops/removes approved
test containers and then removes test network/volume without force. No credentials
or Compose environment values are required for teardown. It uses the project's
`.docker-local` CLI configuration. Docker must be running and available.

## Always clean a verification session

Replace all credential placeholders with disposable URL-safe test credentials first.
These are command templates, not a claim of currently running services:

```powershell
$env:POSTGRES_USER = 'REPLACE_TEST_USER'
$env:POSTGRES_PASSWORD = 'REPLACE_TEST_PASSWORD'
$env:POSTGRES_DB = 'parallax_risk_test'
$env:PARALLAX_DATABASE_URL = 'postgresql+psycopg://REPLACE_TEST_USER:REPLACE_TEST_PASSWORD@postgres:5432/parallax_risk_test'
$env:PARALLAX_TEST_DATABASE_URL = 'postgresql+psycopg://REPLACE_TEST_USER:REPLACE_TEST_PASSWORD@127.0.0.1:55432/parallax_risk_test'
try {
    docker --config .docker-local compose -p parallax-risk-phase10-verification -f docker-compose.yml -f scripts/compose.verify.yml up --wait
    if ($LASTEXITCODE -ne 0) { throw 'Verification stack startup failed' }
    .venv\Scripts\python.exe -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Verification tests failed' }
} finally {
    .\scripts\cleanup_docker.ps1 -Phase 10 -Apply
}
```

For standalone test containers, use `--rm` and the exact verification project's
`com.docker.compose.project` label plus `io.parallax-risk.project=parallax-risk`,
`io.parallax-risk.purpose=verification` and `io.parallax-risk.workspace` set to the
actual repository root. This allows fallback cleanup if the run is interrupted.
Do not add these disposable labels to persistent/normal services.

CI uses `parallax-risk-ci` explicitly and `if: always()` Compose down with disposable
test volumes after logs. It does not select containers by shared image ancestry.

On this maintenance audit there were no Parallax Risk containers/networks/volumes
remaining. Both tagged phase images were retained as useful. Controlled cleanup
guard checks and final inventory are recorded in the [maintenance report](../validation/documentation-maintenance.md).

## Phase 7 helper

Use the retained Phase 7 source/archive for historical replay of
`.\scripts\verify_phase7.ps1`; the current checkout builds the current release and
cannot satisfy that helper's older version assertions. In its matching source it builds
0.7.0, checks HTTP/database/non-root runtime, runs Windows and Linux tests against
isolated PostgreSQL, saves useful logs under `artifacts/local/phase7/` and always
calls Phase 7 scoped cleanup in finally. Its fixed credentials are disposable test
values only. Linux dev dependencies and temporary writable files disappear with
its `--rm` verification container. See [Phase 7 results](../validation/phase-7.md).

## Phase 9 helper

Use the retained Phase 9 source/archive for its historical helper; the current
checkout must use the Phase 10 helper below. In matching Phase 9 source,
`scripts/verify_phase9.ps1` uses parallax-risk-phase9-verification and installed
0.9.0, verifies HTTP/database/non-root operation and runs full Windows/Linux tests
against the isolated PostgreSQL 17 service. `--rm` plus explicit verification labels
scope the disposable test container. Finally invokes Phase 9 ownership-checked
cleanup after saving needed logs/results. Retain useful release/rollback images,
shared layers/cache, production data and unrelated resources. Do not delete files
inside arbitrary containers or use global prune. [Actual inventory](../validation/phase-9.md).

## Phase 10 helper

`scripts/verify_phase10.ps1` uses parallax-risk-phase10-verification and installed
0.10.0. Its full Windows/Linux suites connect to isolated PostgreSQL 17; image hashes,
health/readiness/version/database/runtime UID and actual coverage are retained.
The test-run container uses --rm and explicit ownership labels. Finally removes only
owned disposable phase containers/network/test volume; useful release/rollback images,
shared cache/layers and persistent/unrelated resources remain.
[Actual inventory and verification](../validation/phase-10.md).
