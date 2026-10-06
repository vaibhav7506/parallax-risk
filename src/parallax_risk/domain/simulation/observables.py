"""Reusable research observables; these are statistics, not instrument contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import numpy as np

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_text, require_token
from parallax_risk.domain.models.base import positive
from parallax_risk.domain.simulation.arrays import FloatArray, finite_array, integer
from parallax_risk.domain.simulation.contracts import PathBatch


class PathObservable(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def unit(self) -> str: ...

    @property
    def hash(self) -> str: ...

    def __call__(self, batch: PathBatch) -> FloatArray: ...


class TerminalOperation(StrEnum):
    IDENTITY = "identity"
    LOG = "log"
    SQUARE = "square"
    CALL = "positive_part_above_strike"


@dataclass(frozen=True, slots=True)
class TerminalObservable:
    name: str
    unit: str
    state_index: int
    operation: TerminalOperation = TerminalOperation.IDENTITY
    strike: float | None = None
    multiplier: float = 1.0

    def __post_init__(self) -> None:
        require_token(self.name)
        require_text(self.unit)
        integer(self.state_index, "observable state index", minimum=0)
        require_finite(self.multiplier, name="observable multiplier")
        if not isinstance(self.operation, TerminalOperation):
            raise SimulationError("An explicit terminal operation is required")
        if self.operation == TerminalOperation.CALL:
            if self.strike is None:
                raise SimulationError("Positive-part observable requires a strike")
            positive(self.strike, "observable strike")
        elif self.strike is not None:
            raise SimulationError("Strike is only applicable to the positive-part observable")

    @property
    def hash(self) -> str:
        return content_hash(self)

    def __call__(self, batch: PathBatch) -> FloatArray:
        if self.state_index >= batch.values.shape[2]:
            raise SimulationError("Observable state index is outside the simulated state")
        terminal = batch.values.array[:, -1, self.state_index]
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                if self.operation == TerminalOperation.LOG:
                    result = np.log(terminal)
                elif self.operation == TerminalOperation.SQUARE:
                    result = terminal * terminal
                elif self.operation == TerminalOperation.CALL:
                    # The constructor requires a strike for this branch.
                    assert self.strike is not None
                    result = np.maximum(terminal - self.strike, 0.0)
                else:
                    result = terminal
                result = result * self.multiplier
        except FloatingPointError as error:
            raise NumericalError(
                "Terminal observable is outside its finite numerical domain"
            ) from error
        return finite_array(result, ndim=1, name="terminal observable")
