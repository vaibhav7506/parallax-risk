# Model validation workflow

1. Retain a supported immutable case, exact units/currency, source release and run metadata.
2. Inject production and independently implemented challenger adapters into ValidationLab.
3. Evaluate identical input hashes and compare exact ordered metric/contribution schemas.
4. Retain component differences, residuals, explicit tolerance checks and any open findings.
5. Run justified invariants and actual local perturbation/derivative checks.
6. Supply explicit path and date/grid ladders, evaluate each, retain SEM/confidence bounds
   and both stability and precision failures. Refine grids without changing economics.
7. Select independent risk observations for owned bootstrap, or supply parameter cases
   or a converged calibration with usable covariance for distinct uncertainty bands.
8. Supply hypothetical shocks or dated sourced observations and revalue ordered stresses.
9. Save needed results outside disposable Docker layers, then perform owned verification cleanup.

`src/parallax_risk/application/validation.py` owns injected protocols, comparability and
parameter/calibration workflows; `src/parallax_risk/application/validation_models.py`
bridges to actual production credit/exposure/XVA services. Domain calculations remain
inward and independent of API/persistence. No new database migration, financial HTTP
endpoint, runtime service or required dependency is added. Invalid evidence rejects.

```powershell
python scripts/demo_validation.py
python -m pytest tests/quantitative/test_validation_lab.py tests/unit/test_validation_guards.py tests/integration/test_validation_workflow.py --no-cov
python scripts/check_docs.py
./scripts/verify_phase9.ps1
./scripts/cleanup_docker.ps1 -Phase 9
```

The demo is synthetic and retains failed findings. The focused command intentionally
disables whole-package coverage because it tests only the lab; release acceptance uses
the full branch-inclusive suite with >=95% coverage and live isolated PostgreSQL.
The verification helper executes full Windows and installed-wheel Linux suites and
calls `scripts/cleanup_docker.ps1 -Phase 9 -Apply` in finally. Cleanup only selects
parallax-risk-phase9-verification with ownership labels; normal persistent parallax-risk
resources and other projects are outside scope. Preview is the default.

[Method](../methodology/MODEL_VALIDATION.md), [uncertainty](../methodology/MODEL_UNCERTAINTY.md),
[stress](../methodology/STRESS_SCENARIOS.md), [tutorial](../tutorials/08-FIRST-VALIDATION-RUN.md),
[actual phase evidence](../validation/phase-9.md). Phase 10 mutation/adversarial work,
Phase 11 adds separate research governance; Phase 12 financial APIs remain NOT IMPLEMENTED.

## Phase 10 applicability

Phase 10 extends the lab with injected isolated mutations, bounded comparable-model objectives and actual repeated/ordered diagnostic cases. It retains missed faults and unexplained changes; governance remains outside the workflow.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).
