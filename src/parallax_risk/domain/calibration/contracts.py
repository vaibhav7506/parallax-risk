"""Bounded least-squares contracts, immutable convergence and uncertainty evidence."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from parallax_risk.common.errors import CalibrationError
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_token
from parallax_risk.domain.models.base import Matrix, State, positive


class CalibrationProblem(Protocol):
    """Predictions and quote scales; residual=(model-observed)/scale, order preserved."""

    @property
    def model_name(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    @property
    def parameter_names(self) -> tuple[str, ...]: ...

    @property
    def input_hash(self) -> str: ...

    @property
    def observed(self) -> State: ...

    @property
    def scales(self) -> State: ...

    @property
    def value_unit(self) -> str: ...

    def predict(self, parameters: State) -> State: ...


@dataclass(frozen=True, slots=True)
class ParameterBound:
    name: str
    initial: float
    lower: float
    upper: float

    def __post_init__(self) -> None:
        require_token(self.name)
        for label, value in (
            ("initial", self.initial),
            ("lower", self.lower),
            ("upper", self.upper),
        ):
            require_finite(value, name=label)
        if not self.lower < self.upper or not self.lower <= self.initial <= self.upper:
            raise CalibrationError(
                "Parameter bounds must be finite lower<upper with initial inside"
            )


@dataclass(frozen=True, slots=True)
class CalibrationSettings:
    max_evaluations: int = 1000
    function_tolerance: float = 1e-10
    parameter_tolerance: float = 1e-10
    gradient_tolerance: float = 1e-10
    maximum_condition_number: float = 1e10

    def __post_init__(self) -> None:
        if type(self.max_evaluations) is not int or self.max_evaluations <= 0:
            raise CalibrationError("Maximum optimizer evaluations must be a positive integer")
        for value in (self.function_tolerance, self.parameter_tolerance, self.gradient_tolerance):
            if not 1e-14 <= positive(value, "optimizer tolerance") < 1:
                raise CalibrationError("Optimizer tolerances must be in [1e-14,1)")
        if positive(self.maximum_condition_number, "maximum condition number") <= 1:
            raise CalibrationError("Maximum condition number must exceed one")


class CalibrationStatus(StrEnum):
    CONVERGED = "converged"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ParameterUncertainty:
    """Local unconstrained iid-scaled-residual Gauss-Newton estimate, or explicit absence."""

    jacobian_rank: int
    degrees_of_freedom: int
    condition_number: float | None
    covariance: Matrix | None
    standard_errors: State | None
    unavailable_reason: str | None
    interpretation: str = "local_linear_iid_scaled_residuals; not a confidence guarantee"


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    calibration_id: CalibrationRunId
    model_name: str
    model_version: str
    input_data_hash: str
    configuration_hash: str
    status: CalibrationStatus
    parameter_bounds: tuple[ParameterBound, ...]
    fitted_parameters: State
    predictions: State
    residuals: State
    scaled_residuals: State
    value_unit: str
    rmse: float
    scaled_rmse: float
    maximum_absolute_residual: float
    optimizer_status: int
    termination_message: str
    optimizer_evaluations: int
    objective_evaluations: int
    jacobian_evaluations: int
    optimality: float
    active_bounds: tuple[int, ...]
    uncertainty: ParameterUncertainty
    optimizer: str = "scipy_least_squares_trf_linear_3point_jac_scale"

    def require_converged(self) -> None:
        """Callers can enforce convergence explicitly; no failed result is upgraded."""
        if self.status != CalibrationStatus.CONVERGED:
            raise CalibrationError(
                "Calibration optimizer did not converge; inspect result diagnostics"
            )

    @property
    def parameter_set(self) -> tuple[tuple[str, float], ...]:
        return tuple(
            (bound.name, value)
            for bound, value in zip(self.parameter_bounds, self.fitted_parameters, strict=True)
        )
