# Parallax Risk security scope

Release 0.12.0 adds static opaque-key authentication, explicit RBAC, owner-scoped financial
inputs/jobs/reports, strict nominal/Pydantic ingestion, work/body/rate limits, correlation
and safe structured logging. [Service contracts](docs/methodology/SERVICE.md) define the
exact permissions and [deployment](docs/operations/SERVICE.md) defines transport trust.
This is research software, not enterprise identity/security/regulatory certification.

Generate high-entropy keys; configure only their SHA-256 digests. Never commit or log raw
keys, .env, database URLs or confidential financial inputs. Credential files are local
regular files with explicit limits; CLI rejects remote plaintext HTTP and credentialed
URLs, and disables redirects so keys cannot be forwarded to another origin. Use HTTPS
at a trusted proxy for remote API access; local mode assumes isolated/loopback access.
Exact CORS origins are deliberate and do not replace authentication. Proxy forwarding
trust must be restricted; the guard requires HTTPS scheme in tls_proxy mode.

The API accepts bounded streamed JSON, rejects duplicate keys, NaN/Inf, invalid structure,
compressed payloads and extra fields, and never executes uploaded code or follows a
client-provided server file path. Type names are exact server-selected discriminators,
not dynamic imports. Numerical admission limits are conservative work/buffer controls,
not hard RSS/latency guarantees. Invalid inputs fail explicitly; no silent financial repair.

Governance is a shared research inventory. Reader/analyst/validator/approver/operator
roles are explicit; approvals bind authority to authenticated subject. Financial objects
and runs are owner-scoped. These controls are not enterprise multi-tenancy, signed
approvals or market-data authenticity. SHA-256 evidence hashes are not signatures or
encryption. Ordinary append-only database triggers do not defeat privileged administrators.

Reports preserve actual retained evidence, escaped interpretation and restrictive CSP;
JSON/HTML may contain sensitive evidence. Preserve useful replay/results before disposable
test cleanup and apply local access controls. No automatic retention purge, external
alert sender, HA worker recovery or hard compute cancellation exists. Uncertain claims
remain visible and require inspection; automatic replay could duplicate committed evidence.

An isolated pip-audit 2.10.1 check of exact runtime/development pins using the PyPI
advisory service found no known vulnerabilities on client date 2026-10-02. The JSON/log
result is retained in ignored Phase 12 artifacts. This point-in-time result does not
prove absence of unknown defects, and pins lack artifact hashes. CI repeats the strict
[PyPA dependency audit](https://github.com/pypa/pip-audit); hosted results are not inferred.

Report potential defects privately to the repository owner through a channel they
provide; no dedicated reporting address/SLA exists. Do not post credentials or sensitive
portfolio data. [Docker ownership rules](docs/operations/DOCKER.md) prohibit global prune
and deletion of unrelated services or the normal project's persistent database.
