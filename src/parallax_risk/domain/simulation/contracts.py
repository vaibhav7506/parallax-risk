"""Immutable scientific configuration and simulation provenance, separate from paths."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import SimulationError
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.models.assets import GeometricBrownianMotion, Heston
from parallax_risk.domain.models.base import State, nonnegative
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.rates import HullWhite, Vasicek
from parallax_risk.domain.simulation.arrays import FrozenArray, integer, power_of_two
from parallax_risk.domain.simulation.random import SequenceKind, SequenceSpec

type SupportedProcess = GeometricBrownianMotion | Vasicek | HullWhite | Heston


class Scheme(StrEnum):
    EXACT = "exact"
    EULER = "euler_maruyama"
    HESTON_PROJECTED = "heston_projected_euler"


@dataclass(frozen=True, slots=True)
class TimeGrid:
    """Explicit nonnegative year fractions; no dates/day-count policy is inferred."""

    times: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.times, tuple) or len(self.times) < 2:
            raise SimulationError("Time grid requires at least two immutable time points")
        for time in self.times:
            nonnegative(time, "grid time")
        if any(right <= left for left, right in zip(self.times[:-1], self.times[1:], strict=True)):
            raise SimulationError("Time grid must be strictly increasing")

    @property
    def steps(self) -> int:
        return len(self.times) - 1


@dataclass(frozen=True, slots=True)
class ProcessComponent:
    name: str
    process: SupportedProcess
    initial_state: State
    scheme: Scheme
    state_units: tuple[str, ...]
    measure: str

    def __post_init__(self) -> None:
        require_token(self.name)
        require_token(self.measure)
        if not isinstance(self.process, (GeometricBrownianMotion, Vasicek, HullWhite, Heston)):
            raise SimulationError("Process has no supported vectorized kernel")
        self.process.validate_state(self.initial_state)
        if not isinstance(self.scheme, Scheme):
            raise SimulationError("An explicit discretization scheme is required")
        if self.scheme == Scheme.EXACT and isinstance(self.process, Heston):
            raise SimulationError("Heston has no exact transition; no scheme fallback")
        if self.scheme == Scheme.HESTON_PROJECTED and not isinstance(self.process, Heston):
            raise SimulationError("Projected Heston scheme requires a Heston model")
        require_tuple(self.state_units, str)
        if len(self.state_units) != self.process.state_dimension:
            raise SimulationError("State units must match the component state dimension")
        for unit in self.state_units:
            require_text(unit)

    @property
    def factor_names(self) -> tuple[str, ...]:
        return tuple(f"{self.name}.d{index}" for index in range(self.process.driver_dimension))

    @property
    def state_names(self) -> tuple[str, ...]:
        return tuple(f"{self.name}.s{index}" for index in range(self.process.state_dimension))

    @property
    def innovation_speeds(self) -> tuple[float, ...]:
        if self.scheme == Scheme.EXACT and isinstance(self.process, (Vasicek, HullWhite)):
            return (self.process.speed,)
        return (0.0,) * self.process.driver_dimension


@dataclass(frozen=True, slots=True)
class SimulationRequest:
    components: tuple[ProcessComponent, ...]
    grid: TimeGrid
    path_count: int
    batch_size: int
    sequence: SequenceSpec
    correlation: CorrelationMatrix | None = None

    def __post_init__(self) -> None:
        require_tuple(self.components, ProcessComponent, nonempty=True)
        if len({item.name for item in self.components}) != len(self.components):
            raise SimulationError("Component names must be unique")
        if not isinstance(self.grid, TimeGrid) or not isinstance(self.sequence, SequenceSpec):
            raise SimulationError("Validated time grid and sequence configuration are required")
        integer(self.path_count, "path count")
        integer(self.batch_size, "batch size")
        if self.sequence.antithetic and (self.path_count % 2 or self.batch_size % 2):
            raise SimulationError("Antithetic path and batch sizes must be even")
        if self.sequence.kind == SequenceKind.SOBOL:
            if not power_of_two(self.path_count) or not power_of_two(self.batch_size):
                raise SimulationError("Sobol path and batch sizes must be powers of two")
            if self.path_count > 2**self.sequence.sobol_bits:
                raise SimulationError("Sobol path count exceeds its finite-bit design")
            if self.grid.steps * self.driver_dimension > 21201:
                raise SimulationError("Time-step/factor Sobol dimension exceeds 21201")
        if self.correlation is not None:
            if not isinstance(self.correlation, CorrelationMatrix):
                raise SimulationError("Correlation input requires a validated CorrelationMatrix")
            if self.correlation.factors != self.factor_names:
                raise SimulationError(
                    "Correlation factors must exactly match component driver order"
                )
            self.correlation.cholesky()
            offset = 0
            for item in self.components:
                if (
                    isinstance(item.process, Heston)
                    and self.correlation.values[offset][offset + 1] != 0
                ):
                    raise SimulationError("Heston's pre-loading drivers must remain independent")
                offset += item.process.driver_dimension

    @property
    def factor_names(self) -> tuple[str, ...]:
        return tuple(name for item in self.components for name in item.factor_names)

    @property
    def state_names(self) -> tuple[str, ...]:
        return tuple(name for item in self.components for name in item.state_names)

    @property
    def driver_dimension(self) -> int:
        return sum(item.process.driver_dimension for item in self.components)

    @property
    def state_dimension(self) -> int:
        return sum(item.process.state_dimension for item in self.components)

    @property
    def hash(self) -> str:
        return content_hash(self)


@dataclass(frozen=True, slots=True)
class SimulationMetadata:
    request_hash: str
    engine_version: str
    sequence: SequenceSpec
    algorithm: str
    normal_transform: str
    numpy_version: str
    scipy_version: str
    python_version: str
    platform: str
    source_revision: str | None
    state_names: tuple[str, ...]
    factor_names: tuple[str, ...]
    state_units: tuple[str, ...]
    measures: tuple[str, ...]
    times: tuple[float, ...]
    path_count: int
    batch_size: int
    correlation_hash: str | None
    layout: str = "path,time,state; normals=path,step,pre-loading-driver"
    correlation_policy: str = "Brownian_driver_correlation_with_exact_OU_kernel_covariance"


@dataclass(frozen=True, slots=True)
class PathBatch:
    start_path: int
    values: FrozenArray
    variance_projection_count: int

    def __post_init__(self) -> None:
        integer(self.start_path, "batch start path", minimum=0)
        if not isinstance(self.values, FrozenArray) or len(self.values.shape) != 3:
            raise SimulationError("Path batches require immutable path/time/state buffers")
        integer(self.variance_projection_count, "variance projection count", minimum=0)

    @property
    def path_count(self) -> int:
        return self.values.shape[0]
