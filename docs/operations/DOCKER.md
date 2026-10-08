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
| Release images | Keep current `parallax-risk:0.6.0` and useful `0.5.0`/`0.4.0`/`0.3.0`/`0.2.0`/`0.1.0` rollback/evidence images |
| Normal Compose data/services | Retain; project `parallax-risk` is not a disposable phase verification project |
| Shared base images/layers/build cache | Retain; ownership is not exclusive, future builds can reuse them |
| Other projects or ambiguous resources | Retain; never use global prune or force removal |

## Preview and scoped teardown

PowerShell from the repository root:

```powershell
.\scripts\cleanup_docker.ps1 -Phase 6
.\scripts\cleanup_docker.ps1 -Phase 6 -Apply
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
    docker --config .docker-local compose -p parallax-risk-phase6-verification -f docker-compose.yml -f scripts/compose.verify.yml up --wait
    if ($LASTEXITCODE -ne 0) { throw 'Verification stack startup failed' }
    .venv\Scripts\python.exe -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Verification tests failed' }
} finally {
    .\scripts\cleanup_docker.ps1 -Phase 6 -Apply
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

## Phase 6 helper

Run `.\scripts\verify_phase6.ps1` from PowerShell for the active release. It builds
0.6.0, checks HTTP/database/non-root runtime, runs Windows and Linux tests against
isolated PostgreSQL, saves useful logs under `artifacts/local/phase6/` and always
calls Phase 6 scoped cleanup in finally. Its fixed credentials are disposable test
values only. Linux dev dependencies and temporary writable files disappear with
its `--rm` verification container. See [Phase 6 results](../validation/phase-6.md).
