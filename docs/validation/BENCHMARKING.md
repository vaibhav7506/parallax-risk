# Pricing and model benchmarking

Benchmarks must have an independently derived target, explicit inputs/conventions
and a justified tolerance. Testing a function against the same function does not
challenge quantitative correctness. No external-pricer execution is claimed here.

`tests/quantitative/test_deterministic_pricing.py` uses 50-digit Decimal exponential
targets for discounting and hand-derived cash-flow, par swap and FX parity formulas.
Cases include positive/negative rates, known and projected coupons, distinct discount/
projection curves, explicit payment lag and spot settlement lag. NPV is also compared
to the compensated sum of original signed contribution values.

`tests/unit/test_curves_bootstrap.py` checks deposit/par-swap nodes against derived
discounts and validates all quote repricing residuals. Failure tests use known
bad brackets, iteration limits and stagnation settings, not fabricated convergence.

Small-notional formulas use explicit near-1e-12 absolute currency bounds; million-unit
FX cases allow 1e-8 absolute and 1e-12 relative for cancellation. Exponential/forward
checks and sensitivity tolerances vary by mathematical case; inspect the assertions
and [complete tolerance policy](../methodology/deterministic-pricing.md).

Recorded actual counts/coverage/environment belong to phase reports. The documentation
maintenance update does not turn prior benchmark outcomes into newly run tests.

Phase 3 `tests/quantitative/test_stochastic_models.py` uses independent Gaussian
mean/kernel quadrature for Vasicek and conditioned Hull–White bonds, forward-measure
Gaussian payoff integration for bond calls and an independently integrated Riccati
ODE for the Heston characteristic function, including very short maturities.
The numerical 10.39421856515 Heston case is regression evidence, not vendor validation.
Small-xi Fourier prices approach the known Gaussian call price within 2e-6 currency
units, without a small-xi threshold fallback. Parameter recovery is a separate
internal-consistency test on generated observations, not an independent model benchmark.
See [model tests](../methodology/STOCHASTIC_PROCESSES.md) and
[calibration limits](../methodology/CALIBRATION.md) for exact units and tolerances.
