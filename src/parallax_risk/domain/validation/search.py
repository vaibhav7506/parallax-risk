"""Explicit search bounds, linear plausibility restrictions and optimizer evidence."""

from dataclasses import dataclass

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token, require_tuple
from parallax_risk.domain.simulation.arrays import integer
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.contracts import ModelOutput


@dataclass(frozen=True, slots=True)
class SearchDimension:
    name: str
    unit: str
    lower: float
    upper: float
    rationale: str

    def __post_init__(self) -> None:
        require_token(self.name)
        require_text(self.unit)
        require_text(self.rationale)
        if require_finite(self.lower, name="lower bound") >= require_finite(
            self.upper, name="upper bound"
        ):
            raise DomainValidationError("Search needs finite strictly ordered bounds")


@dataclass(frozen=True, slots=True)
class LinearRestriction:
    name: str
    weights: tuple[float, ...]
    lower: float
    upper: float
    rationale: str

    def __post_init__(self) -> None:
        require_token(self.name)
        require_text(self.rationale)
        require_tuple(self.weights, float, nonempty=True)
        for weight in self.weights:
            require_finite(weight, name="constraint weight")
        if not any(self.weights) or require_finite(
            self.lower, name="constraint lower"
        ) > require_finite(self.upper, name="constraint upper"):
            raise DomainValidationError(
                "Linear restrictions need nonzero weights and ordered limits"
            )


@dataclass(frozen=True, slots=True)
class SearchSpec:
    dimensions: tuple[SearchDimension, ...]
    restrictions: tuple[LinearRestriction, ...]
    key: StreamKey
    metric: str
    source: str
    maximum_iterations: int = 10
    population_multiplier: int = 5
    maximum_evaluations: int = 1000
    convergence_relative: float = 1e-6
    convergence_absolute: float = 1e-9

    def __post_init__(self) -> None:
        require_tuple(self.dimensions, SearchDimension, nonempty=True)
        require_tuple(self.restrictions, LinearRestriction)
        require_token(self.metric)
        require_text(self.source)
        integer(self.maximum_iterations, "optimizer iterations", minimum=0)
        integer(self.population_multiplier, "population multiplier")
        integer(self.maximum_evaluations, "paired model evaluations")
        if (
            not isinstance(self.key, StreamKey)
            or len({d.name for d in self.dimensions}) != len(self.dimensions)
            or len({c.name for c in self.restrictions}) != len(self.restrictions)
            or any(len(c.weights) != len(self.dimensions) for c in self.restrictions)
        ):
            raise DomainValidationError("Search dimensions/restrictions/stream do not align")
        for value in (self.convergence_relative, self.convergence_absolute):
            if require_finite(value, name="optimizer tolerance") < 0:
                raise DomainValidationError("Optimizer tolerances must be nonnegative")
        if self.planned_evaluations > self.maximum_evaluations:
            raise DomainValidationError("Worst-case optimizer evaluations exceed declared budget")

    @property
    def planned_evaluations(self) -> int:
        return (self.maximum_iterations + 1) * max(
            5, self.population_multiplier * len(self.dimensions)
        )


@dataclass(frozen=True, slots=True)
class OptimizerResult:
    parameters: tuple[float, ...]
    objective: float
    converged: bool
    message: str
    iterations: int
    evaluations: int
    implementation: str


@dataclass(frozen=True, slots=True)
class SearchEvaluation:
    parameters: tuple[float, ...]
    production: ModelOutput
    challenger: ModelOutput
    discrepancy: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    specification: SearchSpec
    optimizer: OptimizerResult
    best: SearchEvaluation
    evaluations: tuple[SearchEvaluation, ...]
    interpretation: str = (
        "Best evaluated feasible absolute production/challenger discrepancy; "
        "not a proven global maximum, event probability or regulatory conclusion. "
        "Bounds/constraints express caller-declared plausibility, not authenticated market history."
    )
