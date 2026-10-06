# Monte Carlo estimates, intervals and variance reduction

Phase 4 estimates caller-supplied path observables. Terminal identity, log, square
and positive-part operations are reusable research statistics, not new instrument
or exposure contracts. Each observable declares its name, unit and configuration hash.

## Independent sampling units

`OnlineMoments` merges centered sums using Chan/Welford updates, avoiding subtraction
of large raw second moments. Descriptive path variance uses denominator `n-1`;
calling it unbiased requires independent identically distributed observations.
Invalid, empty, overflowing or unresolved inputs fail explicitly.

For pseudo-random ordinary paths, the sampling units are path observations.
For antithetics, the sampling units are averages of adjacent complete pairs.
The estimator variance is the **sampling-unit** sample variance divided by the
number of independent units; its square root is the standard error. Counting both
members of a pair as independent gives a misleading interval. Raw path descriptive
moments are reported separately from adjusted or paired estimator moments.

Intervals are approximate Student t intervals with `units-1` degrees of freedom
and explicit confidence (default .95). They are exact only in applicable normal
sampling settings and approximate otherwise. At least two independent units are
required. They quantify random error conditional on the model, grid, and fixed
pilot coefficient, not model, calibration, numerical bias or input uncertainty.

One scrambled Sobol design has no IID standard error or confidence interval.
`SimulationService.run` records that absence and leaves convergence standard
errors unset. `replicated_sobol` assigns distinct consecutive substream addresses
to complete designs. Its t interval uses the independent **scramble means**;
`R` scramblings of `N` points have `R` independent units and `R*N` total paths.
The finite-bit midpoint convention's quadrature bias is not included in this interval.

## Control variates and comparisons

For known control expectation `mu_Y`, use `X - beta*(Y-mu_Y)`. `fit_control`
estimates `beta=cov(X,Y)/var(Y)` from explicitly separate pilot sampling units,
then freezes beta. Pilot/evaluation stream addresses must differ. The caller must
supply a valid known expectation and honestly identified sampling units; a different
address cannot detect deliberately mislabelled/reused observations. Constant or
numerically unresolved pilot controls fail, without silently setting beta to zero.
For an antithetic pilot, average both arrays by pair before fitting.

The synthetic terminal-call example uses a separate terminal-spot pilot and its
analytical GBM expectation. Comparisons report estimator-variance ratios at equal
evaluation path counts. A second ratio includes pilot path cost; it is not elapsed
time efficiency and does not include every computational overhead.

Variance reduction is statistic dependent. A linear normal statistic cancels
under antithetics, while an even function such as `Z**2` duplicates information
and can double estimator variance for the same path budget. Controls can worsen
variance with a poor finite pilot or introduce bias with a wrong known expectation.

## Convergence experiments

Per-batch convergence points track mean and valid pseudo sampling-unit standard
error. `path_count_study` uses independent replicates at increasing path counts,
nested prefixes across counts, an explicit reference, empirical RMSE/bias/variance
and a descriptive logarithmic RMSE slope. Counts at different sizes are dependent
through nesting. A zero observed RMSE has no logarithmic slope and is reported
with an absence reason. No monotonic single-run improvement is assumed.

The pseudo asymptotic `N**(-1/2)` expectation applies to suitable finite-variance
IID sampling. Seeded slope tests use broad bounds across multiple independent
replicates; one experiment does not establish a universal rate. Sobol gains depend
on dimension, coordinate ordering and integrand regularity. Brownian bridges,
PCA construction, GPU/distributed methods and advanced convergence certification
are deferred.

Production: `src/parallax_risk/domain/simulation/statistics.py`,
`src/parallax_risk/domain/simulation/controls.py`,
`src/parallax_risk/application/simulation_research.py`.
Tests: `tests/unit/test_simulation_statistics.py`,
`tests/quantitative/test_simulation_convergence.py`.
See [ADR 0010](../decisions/0010-independent-sampling-units.md),
[research notebooks](../../notebooks/02-variance-reduction-convergence.ipynb).
