# Configuration

`src/parallax_risk/application/config.py` defines immutable Pydantic Settings;
`load_settings()` is called explicitly by composition roots. Unknown `PARALLAX_`
variables are rejected, apart from the documented integration-test URL.

| Variable | Meaning / default / constraint |
|---|---|
| PARALLAX_ENVIRONMENT | development by default; development/test/production; production requires DB URL |
| PARALLAX_LOG_LEVEL | INFO; DEBUG/INFO/WARNING/ERROR/CRITICAL |
| PARALLAX_DEFAULT_SEED | 0; uint64; integer or ASCII-digit environment text, never bool/float |
| PARALLAX_DATABASE_URL | Optional outside production; single-host postgresql+psycopg URL, no query/fragment |
| PARALLAX_DATABASE_CONNECT_TIMEOUT_SECONDS | 5; integer 1–30 |
| PARALLAX_TOLERANCES__ABSOLUTE | 1e-12; finite nonnegative dimensionless foundation comparison |
| PARALLAX_TOLERANCES__RELATIVE | 1e-9; finite [0,1), not both tolerances zero |
| PARALLAX_TEST_DATABASE_URL | Test runner's isolated live DB URL; not runtime Settings |

These tolerances are not universal money/calibration/statistical acceptance gates.
Curve bootstrap and sensitivity policies have their own documented units/settings.
Credentials are SecretStr, redacted and excluded from configuration hashes; exported
metadata records whether DB is configured. An invalid URL/error is sanitized by
the operational boundary. URL-encode credential characters.

`python -m parallax_risk config` validates and exports safe effective settings;
`run-context` emits the current configuration digest. Logs and exported metadata
must not contain raw connection URLs. See [security](../../SECURITY.md).

Phase 4 SimulationRequest is an explicit typed scientific configuration, separate
from operational Settings. It records model/scheme, units/measure, grid, paths/batches,
root seed and stream/substream, transform, and ordered optional correlation.
RunContext seed must match the request; a newly generated run ID/time does not affect draws.
Synthetic research functions use an explicit environment-independent configuration hash.

Phase 5 portfolio/CSA/ledger values are supplied explicitly to PortfolioService.
No new environment setting loads books, legal rights, currencies or margin policy.
RunContext preserves the existing configuration envelope.
