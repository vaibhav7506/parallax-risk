# Running and operating the service

Release 0.12.0. [Contracts](../methodology/SERVICE.md), [API](../api/ENDPOINTS.md),
[Docker cleanup](DOCKER.md), [verification](../validation/phase-12.md).

## Local configuration and explicit migration

Install the locked runtime/dev environment as described in README. Generate an opaque
key and digest-only configuration; choose a fresh ignored output directory:

```sh
python scripts/create_service_credentials.py --subject researcher --roles reader analyst validator approver operator
```

This writes api-key.txt (never printed) and credentials.json. On POSIX the key gets
mode 0600; on Windows restrict its ACL to the intended account. The helper does not
provide enterprise provisioning/rotation. Keep the raw key out of Git, .env and logs.
Set PARALLAX_SERVICE_CREDENTIALS to the JSON contents of credentials.json, not the raw
key. Production requires digest credentials and an explicit single-host PostgreSQL URL.
Normal Compose loads its explicitly copied .env; library calls do not auto-load dotenv.
Replace every placeholder in .env.example. PARALLAX_SERVICE_ORIGINS=[] disables CORS.

```sh
docker compose config --quiet
docker compose up --wait postgres
docker compose build api
docker compose run --rm --no-deps api python -c "from sqlalchemy import create_engine; from parallax_risk.application.config import load_settings; from parallax_risk.infrastructure.persistence.migrate import migrate; e=create_engine(load_settings().database_url.get_secret_value(),hide_parameters=True); c=e.begin(); connection=c.__enter__(); migrate(connection); c.__exit__(None,None,None); e.dispose()"
docker compose up --wait api
docker compose exec api parallax-risk check-db
```

The migration is an explicit deployment operation and upgrades from zero through 0011
and 0012. An alternative host migration is `python scripts/migrate_governance.py` with
PARALLAX_DATABASE_URL pointing to your explicitly selected reachable database. Startup
never performs DDL. Back up useful data before schema changes. Destructive downgrade to
base requires explicit allow_destructive opt-in and loses all governance/jobs/objects.
Never use that operation for a normal persistent database cleanup.

Only loopback API 8000 is published by normal Compose; PostgreSQL is internal and its
named volume persists across down/up. The runtime runs as UID 10001. Remote use requires
HTTPS at a trusted proxy, PARALLAX_SERVICE_TRANSPORT=tls_proxy, HTTPS-only exact CORS
origins when needed, and Uvicorn forwarding trust restricted to that proxy. The guard
requires the resulting ASGI scheme to be https. Arbitrary client Forwarded headers are
not proof of TLS. Static API keys and owner scoping do not supply enterprise tenancy,
HA, signed decisions, automatic secrets rotation or regulatory certification.

## Jobs, capacity and failures

Configure PARALLAX_SERVICE_WORKERS=1–4, MAXIMUM_PENDING_JOBS=1–256,
REQUESTS_PER_MINUTE=1–10000 and MAXIMUM_PAYLOAD_BYTES=1024–4194304 under the same
PARALLAX_SERVICE_ prefix. Limits are explicit operational configuration; numerical
settings hashes remain separate. Invalid credentials, origins and integer bounds fail.
Only declared exact CORS origins receive access headers; authentication always applies.

Use /health for liveness and /ready for database/schema/worker health. Inspect /v1/runs
and the retained input/result/lineage when computation or persistence fails. A failed
worker is deliberately not automatically replaced; restart only after inspecting its
claims. Pending work persists through service shutdown. Running work from an interrupted
process stays uncertain; an operator can explicitly abandon only its owned job. A late
running calculation cannot commit success after abandonment. Investigate possible
already-committed lineage before replaying with a fresh idempotency key.

Reports and inputs are sensitive when not synthetic. Store backups/artifacts under
appropriate access controls. The application offers no retention purge or arbitrary
file upload path. Cleanup removes only labelled disposable phase-verification containers,
networks and test volumes, thereby removing their temporary writable files. Useful
release images, shared cache/layers, normal project data and other projects are retained.

## Verified commands and CI

`scripts/verify_phase12.ps1` starts an owned isolated verification PostgreSQL/API stack,
explicitly migrates, exercises HTTP/CLI/sample/reports, runs full Windows and installed
Linux tests, saves evidence and always invokes cleanup_docker.ps1 -Phase 12 -Apply.
-Focused runs the new library/live database/architecture checks only. See actual
[phase evidence](../validation/phase-12.md) for results; successful syntax/config checks
are not a live service verification.

CI performs lint/format/type/docs, all test categories with live PostgreSQL, migrations,
≥95% statement+branch coverage, build, pinned dependency audit and a fresh Compose
financial demonstration. Hosted CI results are not claimed from local executions.
