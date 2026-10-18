# Reproducible service example

The complete real synthetic scenario is `scripts/demo_service.py`, with inputs from
`src/parallax_risk/application/service_examples.py`. Fixtures in `data/sample/service/`
are labelled synthetic and are input evidence, not precomputed risk outputs.
[Deployment steps](../operations/SERVICE.md) configure and migrate the service first.

```sh
python scripts/demo_service.py --server http://127.0.0.1:8000 --credential-file artifacts/local/service-credentials/api-key.txt --subject researcher
parallax-risk query --server http://127.0.0.1:8000 --credential-file artifacts/local/service-credentials/api-key.txt --path /v1/governance/model --limit 20
parallax-risk xva --server http://127.0.0.1:8000 --credential-file artifacts/local/service-credentials/api-key.txt --input artifacts/local/phase12/demo/xva-input.json --idempotency-key my-replay-1 --wait-seconds 180
```

Use the subject actually configured in your generated credential. The demonstration
needs reader/analyst/validator/approver/operator roles and paces requests below the
default quota. It registers model/version, ingests exact book/market/scenarios,
calibrates generated Vasicek discount bonds, feeds actual fitted parameters to correlated
simulation, computes daily collateralized exposure and all XVA components, compares
challengers/capital, runs every validation job, retains weak mutation misses as an open
finding and records an explicitly synthetic conditional decision. It replays the
retained XVA input and requires identical financial-result digests, then creates and
retrieves seven JSON/HTML pairs. Small path counts do not prove accuracy or convergence.

The sample exposure horizon is 30 calendar days; capital uses a complete 365-day grid.
Daily two-way zero-haircut USD cash collateral uses threshold USD 5, MTA/IA zero,
zero settlement lag, 10 calendar-day MPOR metadata. The exposure engine preserves its
alive-path/grid-EAD limitation; it does not infer default-conditioned MPOR closeout.
Externally supplied segregated posted IM is USD 10. ACT/365F times and explicit 3%
deterministic origin discounting are research assumptions. Mean/variance/quantile
results retain their original statistical semantics. Recovery/funding data are synthetic.

The output directory includes summary, retained JobInput files and 14 reports. It is
ignored by Git. Retain these before disposable test cleanup. Re-running creates fresh
governance IDs while financial inputs/seeds are deterministic. Replay uses a fresh
Idempotency-Key; repeating the same key returns the first job.
