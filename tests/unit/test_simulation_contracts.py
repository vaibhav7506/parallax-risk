from dataclasses import replace

import numpy as np
import pytest

from parallax_risk.common.errors import DomainValidationError, SimulationError
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.simulation.arrays import FrozenArray, finite_array
from parallax_risk.domain.simulation.contracts import PathBatch, Scheme, TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import SequenceKind
from tests.fixtures.simulation import component, request


@pytest.mark.parametrize(
    "times",
    [
        [],
        (),
        (0.0,),
        (-1.0, 0.0),
        (0.0, 0.0),
        (0.0, -1.0),
        (0.0, float("nan")),
        (0.0, True),
        (0.0, "1"),
    ],
)
def test_time_grid_rejects_invalid_conventions(times):
    with pytest.raises((DomainValidationError, ArithmeticError)):
        TimeGrid(times)


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "bad name"},
        {"measure": ""},
        {"process": object()},
        {"initial_state": (0.0,)},
        {"initial_state": [100.0]},
        {"scheme": "exact"},
        {"scheme": Scheme.HESTON_PROJECTED},
        {"state_units": []},
        {"state_units": ()},
        {"state_units": ("",)},
        {"state_units": ("USD", "rate")},
    ],
)
def test_component_rejects_ambiguous_or_unsupported_inputs(changes):
    with pytest.raises((DomainValidationError, ArithmeticError)):
        replace(component(), **changes)


def test_heston_exact_rejected_and_state_driver_names_are_stable():
    heston = Heston(1.5, 0.04, 0.3, -0.6, 0.03)
    with pytest.raises(SimulationError, match="no exact"):
        component(heston, state=(100.0, 0.04))
    item = component(heston, state=(100.0, 0.04), scheme=Scheme.HESTON_PROJECTED)
    assert item.factor_names == ("asset.d0", "asset.d1")
    assert item.state_names == ("asset.s0", "asset.s1")
    assert item.innovation_speeds == (0.0, 0.0)


@pytest.mark.parametrize(
    "changes",
    [
        {"components": []},
        {"components": ()},
        {"components": (component(), component())},
        {"grid": (0, 1)},
        {"sequence": 4},
        {"path_count": 0},
        {"batch_size": True},
        {"correlation": 4},
        {"correlation": CorrelationMatrix(("wrong",), ((1.0,),))},
    ],
)
def test_request_rejects_bad_dimensions_and_allocation(changes):
    with pytest.raises(DomainValidationError):
        replace(request(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"path_count": 3},
        {"batch_size": 3},
        {"grid": TimeGrid(tuple(float(x) for x in range(21203)))},
        {"path_count": 2**31},
    ],
)
def test_sobol_request_enforces_complete_design(changes):
    with pytest.raises(SimulationError):
        replace(request(kind=SequenceKind.SOBOL), **changes)


@pytest.mark.parametrize("changes", [{"path_count": 3}, {"batch_size": 3}])
def test_pair_boundaries_are_preserved(changes):
    with pytest.raises(SimulationError):
        replace(request(antithetic=True), **changes)


def test_heston_correlation_cannot_be_applied_twice():
    item = component(
        Heston(1.5, 0.04, 0.3, -0.6, 0.03), state=(100.0, 0.04), scheme=Scheme.HESTON_PROJECTED
    )
    correlation = CorrelationMatrix(item.factor_names, ((1.0, -0.6), (-0.6, 1.0)))
    with pytest.raises(SimulationError, match="remain independent"):
        replace(request(), components=(item,), correlation=correlation)
    identity = CorrelationMatrix(item.factor_names, ((1.0, 0.0), (0.0, 1.0)))
    valid = replace(request(paths=4), components=(item,), correlation=identity)
    assert valid.driver_dimension == valid.state_dimension == 2


def test_published_buffer_is_deeply_immutable_and_c_ordered():
    working = np.arange(24.0).reshape(2, 3, 4)
    frozen = FrozenArray.from_array(working[:, :, ::-1])
    expected = frozen.array.copy()
    working[:] = -1
    assert np.array_equal(frozen.array, expected)
    assert frozen.nbytes == 24 * 8
    assert frozen.array.flags.c_contiguous
    with pytest.raises(ValueError):
        frozen.array.setflags(write=True)
    with pytest.raises(ValueError):
        frozen.array[0, 0, 0] = 4
    assert frozen.hash == FrozenArray.from_array(expected).hash
    assert frozen.hash != FrozenArray(frozen.payload, (4, 3, 2)).hash


@pytest.mark.parametrize(
    "payload,shape",
    [
        (bytearray(8), (1,)),
        (b"", ()),
        (b"", []),
        (b"", (0,)),
        (b"", (1,)),
        (np.asarray([np.inf]).tobytes(), (1,)),
    ],
)
def test_frozen_array_rejects_invalid_buffers(payload, shape):
    with pytest.raises(SimulationError):
        FrozenArray(payload, shape)


@pytest.mark.parametrize(
    "value,ndim",
    [
        ([], 1),
        (np.asarray([1], dtype=np.int64), 1),
        (np.asarray([], dtype=np.float64), 1),
        (np.asarray([np.nan]), 1),
        (np.asarray([1.0]), 2),
    ],
)
def test_array_contract_has_no_coercion(value, ndim):
    with pytest.raises(SimulationError):
        finite_array(value, ndim=ndim, name="fixture")


def test_engine_boundary_and_metadata():
    engine = MonteCarloEngine()
    with pytest.raises(SimulationError):
        engine.metadata(4)
    with pytest.raises(SimulationError):
        list(engine.iter_batches(4))
    with pytest.raises(DomainValidationError):
        engine.metadata(request(), source_revision=" ")
    metadata = engine.metadata(request(), source_revision="explicit-source-revision")
    assert metadata.request_hash == request().hash
    assert metadata.source_revision == "explicit-source-revision"
    assert metadata.state_units == component().state_units
    assert metadata.measures == ("Q",)
    assert metadata.engine_version == "0.4.0"
    with pytest.raises(SimulationError):
        FrozenArray.from_array([])


@pytest.mark.parametrize(
    "start,values,projections",
    [
        (-1, FrozenArray.from_array(np.ones((1, 2, 1))), 0),
        (0, np.ones((1, 2, 1)), 0),
        (0, FrozenArray.from_array(np.ones((1, 2))), 0),
        (0, FrozenArray.from_array(np.ones((1, 2, 1))), -1),
    ],
)
def test_path_batch_contract_rejects_malformed_published_evidence(start, values, projections):
    with pytest.raises(SimulationError):
        PathBatch(start, values, projections)
