import numpy as np
import pytest
from scipy.special import ndtri
from scipy.stats import qmc

from parallax_risk.common.errors import SimulationError
from parallax_risk.domain.simulation.random import (
    NormalStream,
    SequenceKind,
    SequenceSpec,
    StreamKey,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", -1),
        ("seed", 2**64),
        ("seed", True),
        ("seed", "1"),
        ("stream", -1),
        ("stream", 2**32),
        ("substream", False),
        ("substream", 1.2),
    ],
)
def test_stream_address_is_strict(field, value):
    arguments = {"seed": 4, "stream": 0, "substream": 0, field: value}
    with pytest.raises(SimulationError):
        StreamKey(**arguments)


@pytest.mark.parametrize(
    "changes",
    [
        {"key": 2},
        {"kind": "pseudo"},
        {"antithetic": 1},
        {"sobol_bits": 0},
        {"sobol_bits": 53},
        {"sobol_bits": True},
        {"kind": SequenceKind.SOBOL, "antithetic": True},
    ],
)
def test_sequence_selection_is_explicit(changes):
    with pytest.raises(SimulationError):
        SequenceSpec(**({"key": StreamKey(7)} | changes))


@pytest.mark.parametrize(
    "kind,anti",
    [(SequenceKind.PSEUDO, False), (SequenceKind.PSEUDO, True), (SequenceKind.SOBOL, False)],
)
def test_normal_stream_replay_and_batch_partition(kind, anti):
    spec = SequenceSpec(StreamKey(9123, 8, 4), kind, anti)
    whole = NormalStream(spec, 6, 64).draw(64)
    sliced = NormalStream(spec, 6, 64)
    batched = np.concatenate([sliced.draw(8) for _ in range(8)])
    assert np.array_equal(whole, batched)
    assert sliced.generated_paths == 64
    if anti:
        assert np.array_equal(whole[0::2], -whole[1::2])
    with pytest.raises(SimulationError, match="exceeds"):
        sliced.draw(2)


def test_addressed_streams_do_not_depend_on_allocation_order():
    keys = [StreamKey(7, 1, 2), StreamKey(7, 1, 3), StreamKey(7, 2, 2), StreamKey(8, 1, 2)]
    first = {key: key.generator().standard_normal(10000) for key in keys}
    reverse = {key: key.generator().standard_normal(10000) for key in reversed(keys)}
    for key in keys:
        assert np.array_equal(first[key], reverse[key])
    correlations = np.corrcoef(np.asarray(list(first.values())))
    assert np.max(np.abs(correlations - np.eye(4))) < 0.05


def test_sobol_is_complete_midpoint_design_with_explicit_rng():
    key = StreamKey(983, 4, 8)
    spec = SequenceSpec(key, SequenceKind.SOBOL, sobol_bits=3)
    uniforms = qmc.Sobol(2, scramble=True, bits=3, rng=key.generator()).random_base2(3)
    expected = ndtri(uniforms + 0.5 / 8)
    actual = NormalStream(spec, 2, 8).draw(8)
    assert np.array_equal(actual, expected)
    assert np.all(np.isfinite(actual))
    assert spec.algorithm == "Sobol.LMS+shift"
    assert spec.normal_transform == "ndtri_midpoint_grid"
    assert SequenceSpec(key).algorithm == "PCG64DXSM.standard_normal"


@pytest.mark.parametrize(
    "spec,dimension,paths",
    [
        (2, 1, 8),
        (SequenceSpec(StreamKey(7)), 0, 8),
        (SequenceSpec(StreamKey(7)), 1, True),
        (SequenceSpec(StreamKey(7), antithetic=True), 1, 3),
        (SequenceSpec(StreamKey(7), SequenceKind.SOBOL), 21202, 8),
        (SequenceSpec(StreamKey(7), SequenceKind.SOBOL), 1, 3),
        (SequenceSpec(StreamKey(7), SequenceKind.SOBOL, sobol_bits=2), 1, 8),
    ],
)
def test_invalid_stream_design_is_rejected(spec, dimension, paths):
    with pytest.raises(SimulationError):
        NormalStream(spec, dimension, paths)


def test_invalid_draw_preserves_stream_position():
    ordinary = NormalStream(SequenceSpec(StreamKey(1)), 1, 8)
    with pytest.raises(SimulationError):
        ordinary.draw(0)
    assert ordinary.generated_paths == 0
    paired = NormalStream(SequenceSpec(StreamKey(1), antithetic=True), 1, 8)
    with pytest.raises(SimulationError, match="pairs"):
        paired.draw(3)
    sobol = NormalStream(SequenceSpec(StreamKey(1), SequenceKind.SOBOL), 1, 8)
    with pytest.raises(SimulationError, match="powers"):
        sobol.draw(3)
    assert paired.generated_paths == sobol.generated_paths == 0
