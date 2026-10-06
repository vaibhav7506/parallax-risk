"""Streaming vectorized paths with exact Gaussian innovation covariance on each step."""

import math
import platform
from collections.abc import Iterator

import numpy as np
import scipy

from parallax_risk.common.errors import SimulationError
from parallax_risk.domain._validation import require_text
from parallax_risk.domain.models.base import ou_loading, positive
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.simulation.arrays import FrozenArray
from parallax_risk.domain.simulation.contracts import (
    PathBatch,
    SimulationMetadata,
    SimulationRequest,
)
from parallax_risk.domain.simulation.kernels import step_batch
from parallax_risk.domain.simulation.random import NormalStream


def innovation_correlation(request: SimulationRequest, dt: float) -> CorrelationMatrix:
    """Normalize integrals of exp(-a*(dt-s)) Brownian kernels, not just rho*dW.

    Exact OU factors have a>0, exact GBM/log-spot and Euler drivers have a=0.
    This preserves Brownian cross-factor rho while allowing unequal OU speeds.
    Heston's internal loading is applied later by its selected numerical scheme.
    """
    dt = positive(dt, "innovation time step")
    speeds = tuple(speed for item in request.components for speed in item.innovation_speeds)
    base = request.correlation
    values = np.eye(request.driver_dimension, dtype=np.float64)

    def integral(speed: float) -> float:
        return dt if speed == 0 else ou_loading(speed, dt)

    for left in range(len(speeds)):
        for right in range(left):
            rho = 0.0 if base is None else base.values[left][right]
            if rho != 0:
                covariance = integral(speeds[left] + speeds[right])
                normalized = covariance / math.sqrt(integral(2 * speeds[left]))
                normalized /= math.sqrt(integral(2 * speeds[right]))
                values[left, right] = values[right, left] = rho * normalized
    tolerance = 1e-12 if base is None else base.psd_tolerance
    return CorrelationMatrix(
        request.factor_names, tuple(tuple(float(x) for x in row) for row in values), tolerance
    )


class MonteCarloEngine:
    """Stateless factory: each iteration owns its RNG and materializes one path batch."""

    version = "0.4.0"

    def metadata(
        self, request: SimulationRequest, *, source_revision: str | None = None
    ) -> SimulationMetadata:
        if not isinstance(request, SimulationRequest):
            raise SimulationError("Simulation requires an immutable validated request")
        if source_revision is not None:
            require_text(source_revision)
        return SimulationMetadata(
            request.hash,
            self.version,
            request.sequence,
            request.sequence.algorithm,
            request.sequence.normal_transform,
            np.__version__,
            scipy.__version__,
            platform.python_version(),
            platform.platform(),
            source_revision,
            request.state_names,
            request.factor_names,
            tuple(unit for item in request.components for unit in item.state_units),
            tuple(item.measure for item in request.components),
            request.grid.times,
            request.path_count,
            request.batch_size,
            None if request.correlation is None else request.correlation.hash,
        )

    def iter_batches(self, request: SimulationRequest) -> Iterator[PathBatch]:
        if not isinstance(request, SimulationRequest):
            raise SimulationError("Simulation requires an immutable validated request")
        factors = request.driver_dimension
        stream = NormalStream(request.sequence, request.grid.steps * factors, request.path_count)
        transitions = tuple(
            (
                left,
                right - left,
                np.asarray(innovation_correlation(request, right - left).cholesky()),
            )
            for left, right in zip(request.grid.times[:-1], request.grid.times[1:], strict=True)
        )
        initial = np.asarray(tuple(x for item in request.components for x in item.initial_state))
        for start in range(0, request.path_count, request.batch_size):
            count = min(request.batch_size, request.path_count - start)
            raw = stream.draw(count).reshape(count, request.grid.steps, factors)
            paths = np.empty(
                (count, len(request.grid.times), request.state_dimension), dtype=np.float64
            )
            paths[:, 0, :] = initial
            projection_count = 0
            for step, (time, dt, loading) in enumerate(transitions):
                # Fixed factor reduction order avoids batch-size-dependent BLAS dispatch.
                shocks = np.zeros((count, factors), dtype=np.float64)
                for column in range(factors):
                    for driver in range(column + 1):
                        shocks[:, column] += loading[column, driver] * raw[:, step, driver]
                state_offset = driver_offset = 0
                for item in request.components:
                    state_end = state_offset + item.process.state_dimension
                    driver_end = driver_offset + item.process.driver_dimension
                    updated, projected = step_batch(
                        item,
                        time,
                        paths[:, step, state_offset:state_end],
                        dt,
                        shocks[:, driver_offset:driver_end],
                    )
                    paths[:, step + 1, state_offset:state_end] = updated
                    projection_count += projected
                    state_offset, driver_offset = state_end, driver_end
            yield PathBatch(start, FrozenArray.from_array(paths), projection_count)
