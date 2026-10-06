from dataclasses import replace

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import StreamKey
from tests.fixtures.simulation import request


@given(seed=st.integers(min_value=0, max_value=2**64 - 1), pairs=st.integers(2, 32))
@settings(max_examples=30, deadline=None)
def test_antithetic_log_paths_preserve_pair_product_and_replay(seed, pairs):
    config = request(paths=2 * pairs, batch=8, antithetic=True)
    config = replace(config, sequence=replace(config.sequence, key=StreamKey(seed)))
    engine = MonteCarloEngine()
    first = np.concatenate([batch.values.array for batch in engine.iter_batches(config)])
    second = np.concatenate(
        [batch.values.array for batch in engine.iter_batches(replace(config, batch_size=2 * pairs))]
    )
    assert np.array_equal(first, second)
    assert np.all(first > 0) and np.all(np.isfinite(first))
    # Exact log-GBM reflection cancels stochastic log increments at each time.
    times = np.asarray(config.grid.times)
    expected = 2 * np.log(100.0) + 2 * (0.05 - 0.5 * 0.2**2) * times
    assert np.allclose(
        np.log(first[0::2, :, 0]) + np.log(first[1::2, :, 0]), expected, rtol=1e-13, atol=1e-13
    )
