# Your first simulation research run

Use the locked development environment described in [setup](../../DEVELOPMENT.md).
Every experiment here uses synthetic inputs and calls the production library.

1. Run `python scripts/demo_simulation.py`. JSON contains GBM/Vasicek analytical
   comparisons, plain/antithetic/control estimates, and pseudo/Sobol path-count studies.
2. Repeat with the same source/environment. JSON is identical; benchmark timings
   and notebook execution timestamps are deliberately not replayable values.
3. Inspect estimator sampling units. Antithetics count pairs; Sobol inference counts
   independent scramblings. A single Sobol design records no IID interval.
4. Run `python scripts/benchmark_simulation.py`. Preserve measured environment,
   timing, immutable buffer sizes and traced allocation peaks; tracing is not RSS.
5. Run `python scripts/execute_notebooks.py`. It uses the current interpreter through
   a workspace-local kernel spec, executes both notebooks, saves successful outputs,
   and explicitly shuts down its kernels. Runtime files/evidence go under
   `artifacts/local/phase4/`. No global kernel installation is needed.

- [Moments and replay notebook](../../notebooks/01-monte-carlo-reproducibility.ipynb)
- [Variance reduction and convergence notebook](../../notebooks/02-variance-reduction-convergence.ipynb)

The first notebook shows moment references and stream metadata. The second displays
actual estimator gains, a measured RMSE plot and independent-scramble inference.
Cells organize/plot production results without reimplementing stochastic formulas.

For custom work, supply explicit units, measure, initial states, schemes and
correlations through [the workflow](../workflows/SIMULATION_WORKFLOW.md).
Keep a separate control pilot and preserve known expectations. These experiments
do not price counterparty default losses or establish real-market accuracy.
