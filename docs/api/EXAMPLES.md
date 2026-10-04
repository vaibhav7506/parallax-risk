# Operational examples

Start a local configured service with the [development commands](../../DEVELOPMENT.md).
Then PowerShell examples:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/version
```

Use port 58000 when running the test override. Ready requires a started service and
real DB connectivity; an unconfigured development service can be live but unready.
No service is kept running after disposable verification cleanup.

```sh
python -m parallax_risk --help
python -m parallax_risk version
python -m parallax_risk config
python -m parallax_risk run-context
python -m parallax_risk check-db
```

Version/config/context output is JSON; context workflow logs use stderr and IDs/time
are fresh unless library creation receives injected values. Check-db requires an
explicit URL and real DB. Pricing examples use the [tutorial](../tutorials/01-FIRST-PRICING-RUN.md),
not an invented HTTP request.
