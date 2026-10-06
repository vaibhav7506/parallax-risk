# Geometric Brownian motion

## Intuition and mathematics

GBM gives a positive asset price with proportional Gaussian shocks and constant
relative volatility. `dS=mu S dt+sigma S dW`, with S>0, finite mu and sigma>=0.
mu is annual drift; sigma is dimensionless/sqrt(year). The caller selects the
measure and drift. For risk-neutral equity with continuous dividend yield q and
deterministic rate r, mu=r-q; for FX it is domestic minus foreign rate. No market
convention, rate lookup or measure is inferred by this primitive.

Exact transition: `S_next=S exp[(mu-sigma²/2)h+sigma sqrt(h)z]`, where z is a supplied
standard-normal shock. Euler: `S_next=S+mu S h+sigma S sqrt(h)z`.

## Implementation, example and tests

GeometricBrownianMotion lives in `src/parallax_risk/domain/models/assets.py` and
implements the [common process interface](STOCHASTIC_PROCESSES.md). Checked
exponentiation rejects overflow/zero underflow; Euler rejects a nonpositive proposal.
No absolute-value or clipping correction is made.

```python
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.discretization import ExactTransition

spot = ExactTransition().step(GeometricBrownianMotion(0.02, 0.20), 0.0, (100.0,), 0.5, (-0.7,))
```

`tests/quantitative/test_stochastic_models.py` checks the exact formula and local
Euler refinement. `tests/property/test_model_invariants.py` checks positivity over
bounded finite spot/shock inputs. `tests/unit/test_model_guards.py` rejects malformed
and out-of-domain data.

## Limitations

This constant-coefficient process omits smiles, jumps, stochastic rates and discrete
dividends. It has no calibration objective in Phase 3; required calibration examples
use rates and Heston. Phase 4 implements terminal-distribution, known-moment and path-count studies with
explicit pseudo/Sobol streams; see [Monte Carlo](MONTE_CARLO.md).
