# Stochastic process and discretization contracts

## Intuition

A process describes how a market state changes and how shocks affect it. A numerical
scheme turns those coefficients into one step. Keeping them separate lets a reviewer
compare exact and approximate dynamics without hiding random generation in a model.

## Mathematics and units

The common interface represents `dX=b(t,X)dt+L(t,X)dZ`, with independent standard
Brownian factors Z. Drift is a state vector; diffusion is a matrix whose rows are
state components and columns are independent drivers. State and supplied shocks
are immutable finite tuples. Time and step size are explicit year fractions; this
interface does not infer dates/day counts. A shock tuple contains standardized
normal realizations, not Brownian increments already multiplied by sqrt(dt).

## Implementation

`src/parallax_risk/domain/models/base.py` defines StochasticProcess, ExactProcess
and Discretization protocols and finite/domain validation. No process generates
random numbers. `src/parallax_risk/domain/models/discretization.py` implements:

| Scheme | Implemented step | Numerical contract |
|---|---|---|
| EulerMaruyama | X+b dt+L sqrt(dt) z | Strong order 1/2, weak order 1 under standard regularity assumptions; invalid output rejected |
| ExactTransition | Dispatch to a supported analytical transition | Vasicek, Hull–White and GBM marginal state; unsupported Heston request raises ModelError |
| HestonProjectedEuler | Log-Euler spot, projected Euler variance | Nonnegative variance and explicit projection diagnostic; boundary bias, no general order claimed |

The exact rate transitions exclude the joint stochastic integral of rates required
for pathwise discounting. Euler can propose negative GBM spot/Heston variance; this
fails instead of clipping. Zero steps preserve valid state but still validate time,
state and shock dimension/finiteness. No automatic discretization fallback exists.

## Example and tests

```python
from parallax_risk.domain.models.discretization import ExactTransition
from parallax_risk.domain.models.rates import Vasicek

next_rate = ExactTransition().step(Vasicek(0.4, 0.05, 0.02), 0.0, (0.01,), 0.25, (0.5,))
```

`tests/quantitative/test_stochastic_models.py` checks exact moments, supplied-shock
loadings and local Euler/exact refinement. Local refinement is not a Monte Carlo
strong-convergence study. `tests/unit/test_model_guards.py` checks invalid parameters,
state, zero-time boundaries, unsupported schemes and finite arithmetic.
`tests/property/test_model_invariants.py` checks positive prices and curve fitting.

## Limitations

Phase 4 random engines, paths, time grids, batching, convergence confidence intervals
and variance reduction are NOT IMPLEMENTED. [Rate](VASICEK.md),
[Hull–White](HULL_WHITE.md), [GBM](GBM.md), [Heston](HESTON.md) and
[correlation](CORRELATION.md) documents state each model's narrower assumptions.
