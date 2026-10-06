# Simulation research workflow

1. Create typed ProcessComponents with explicit model, state, units, measure and scheme.
2. Specify year-fraction grid, paths/batch size, root seed and stream/substream address.
3. Supply a validated ordered Brownian-driver correlation when required. Heston's
   pre-loading pair remains independent; no automatic repair is requested.
4. Inject `MonteCarloEngine` and safe WorkflowLogger into `SimulationService`.
   The RunContext root seed must match the request. Run ID/time do not drive draws.
5. Supply an observable with name, unit and hash. The engine yields immutable
   path batches; the service checks contiguous batches and aligned observations.
6. Preserve metadata, descriptive moments, estimator/absence reason, convergence
   points, projections and optional separate pilot/control evidence.
7. For Sobol inference, run at least two independently addressed complete scramblings.
8. Compare path counts or variance reductions through the production experiment
   functions. Preserve their references, seeds, work counts and limitations.

No HTTP endpoint, job queue, portfolio, netting, collateral, exposure, stochastic
discount integral or XVA result is added. Research outputs do not persist to PostgreSQL.
The operational health/readiness/version interfaces remain available.

```python
from parallax_risk.application.simulation_examples import moment_experiment

result = moment_experiment(paths=16384)
assert result.is_synthetic
assert result.gbm.estimate is not None
```

See [first research run](../tutorials/03-FIRST-SIMULATION-RUN.md),
[paths](../methodology/MONTE_CARLO.md), [statistics](../methodology/MONTE_CARLO_STATISTICS.md),
[reproduction](../REPRODUCIBILITY.md) and [phase report](../validation/phase-4.md).
