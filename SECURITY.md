# Parallax Risk security scope

Release 0.6.0 is an educational/research implementation, not production trading/risk
software or security/regulatory certification. No security support SLA or enterprise
hardening claim is made. Older release artifacts are rollback/history evidence.

The operational API has no authentication, authorization, request-ID middleware,
rate limiting, job submission or financial upload endpoint. Bind it to loopback or
isolated development networks. Financial endpoints and security hardening are
DEFERRED to Phase 12. Generated OpenAPI is not an authorization layer.

Keep `.env`, database credentials and sensitive run inputs out of Git/logs. Settings
export only redacted metadata; credentials are excluded from the configuration hash.
Database failures are sanitized, with bounded timeouts. PostgreSQL is internal to
normal Compose; only the disposable test override publishes a loopback database port.
Persistent volumes must not be removed by test cleanup.

Market ingestion forbids extra fields, nonfinite/boolean/numeric-text rates and
implicit epoch date/instant coercion. The demo reads a fixed local synthetic fixture.
There is no arbitrary upload/deserialization or untrusted-code execution workflow.
Calibration also uses strict discriminated numeric/provenance inputs, finite bounds
and explicit model domains; examples read fixed synthetic fixtures. No financial
upload/API calibration job is exposed.
Do not introduce pickle/eval or unsanitized file paths as shortcuts.

Locks provide exact versions but no artifact hashes. Review dependency changes and
rerun applicable checks; no vulnerability scan is claimed by `pip check` (which
checks dependency consistency only). Docker ownership checks are documented in
[Docker operations](docs/operations/DOCKER.md); global prune is forbidden here.

Report potential vulnerabilities directly to the repository owner through a private
channel they provide. No dedicated reporting address is configured. Do not post
credentials or exploit details in a public issue; record sanitized impact and affected
version/module. Tests and instructions must never require real financial secrets.

Phase 5 books/ledgers contain potentially sensitive trade/legal/cash data. The local
synthetic demo is explicitly labelled; safe logs omit those fields. Portfolio hashes
are content digests, not encryption, signatures, authorization or proof of legal rights.
No external settlement/payment or authenticated financial API is added.

Phase 6 exposure buffers and default scenarios can also contain sensitive derived
trade information. Preserve them only in authorized local artifact storage. This
release adds no financial HTTP route, authentication or external publication.
