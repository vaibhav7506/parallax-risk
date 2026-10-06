"""Pilot-fitted control variates; known expectations and independent pilot are explicit."""

from dataclasses import dataclass

import numpy as np

from parallax_risk.common.errors import NumericalError, SimulationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.simulation.arrays import FloatArray, finite_array, integer
from parallax_risk.domain.simulation.random import StreamKey


@dataclass(frozen=True, slots=True)
class ControlVariate:
    coefficient: float
    known_mean: float
    pilot_key: StreamKey
    pilot_observations: int
    control_name: str

    def __post_init__(self) -> None:
        require_finite(self.coefficient, name="control coefficient")
        require_finite(self.known_mean, name="known control expectation")
        if not isinstance(self.pilot_key, StreamKey):
            raise SimulationError("Control variate requires its pilot stream address")
        integer(self.pilot_observations, "pilot observations", minimum=2)
        if not isinstance(self.control_name, str) or not self.control_name.strip():
            raise SimulationError("Control variate requires an explicit control name")

    def adjust(
        self, target: FloatArray, control: FloatArray, *, evaluation_key: StreamKey
    ) -> FloatArray:
        finite_array(target, ndim=1, name="target values")
        finite_array(control, ndim=1, name="control values")
        if target.shape != control.shape:
            raise SimulationError("Target and control observations must align")
        if not isinstance(evaluation_key, StreamKey) or evaluation_key == self.pilot_key:
            raise SimulationError("Evaluation must use a different explicit stream from the pilot")
        try:
            with np.errstate(over="raise", invalid="raise"):
                adjusted = target - self.coefficient * (control - self.known_mean)
        except FloatingPointError as error:
            raise NumericalError("Control adjustment overflowed") from error
        finite_array(adjusted, ndim=1, name="controlled observations")
        return adjusted


def fit_control(
    target: FloatArray,
    control: FloatArray,
    *,
    known_mean: float,
    pilot_key: StreamKey,
    control_name: str,
) -> ControlVariate:
    """Fit cov(target,control)/var(control) on independent pilot sampling units.

    Pair average both pilot arrays before calling when the pilot is antithetic.
    A constant or numerically unresolved control fails; there is no silent beta=0.
    """
    finite_array(target, ndim=1, name="pilot target")
    finite_array(control, ndim=1, name="pilot control")
    if target.shape != control.shape or target.size < 2:
        raise SimulationError("Control pilot requires at least two aligned observations")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            centered_x, centered_y = target - np.mean(target), control - np.mean(control)
            denominator = float(np.sum(centered_y * centered_y))
            if denominator <= np.finfo(np.float64).tiny:
                raise SimulationError("Control has zero or numerically unresolved pilot variance")
            beta = float(np.sum(centered_x * centered_y)) / denominator
    except FloatingPointError as error:
        raise NumericalError("Control pilot regression overflowed") from error
    return ControlVariate(beta, known_mean, pilot_key, int(target.size), control_name)
