"""Strict finite bounded SciPy least-squares with local identification diagnostics."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import CalibrationError, ParallaxError
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.calibration.contracts import (
    CalibrationProblem,
    CalibrationResult,
    CalibrationSettings,
    CalibrationStatus,
    ParameterBound,
    ParameterUncertainty,
)
from parallax_risk.domain.models.base import State, vector


def _uncertainty(
    jacobian: NDArray[np.float64],
    scaled: State,
    active: tuple[int, ...],
    converged: bool,
    settings: CalibrationSettings,
) -> ParameterUncertainty:
    """SVD, no pseudo-inverse uncertainty for nonidentification or active constraints."""
    if not np.all(np.isfinite(jacobian)):
        raise CalibrationError("Optimizer returned a non-finite Jacobian")
    _, singular, vt = np.linalg.svd(jacobian, full_matrices=False)
    n = jacobian.shape[1]
    dof = len(scaled) - n
    threshold = np.finfo(float).eps * max(jacobian.shape) * singular[0]
    rank = int(np.sum(singular > threshold))
    condition = float(singular[0] / singular[-1]) if rank == n else None
    reason: str | None = None
    if not converged:
        reason = "optimizer_did_not_converge"
    elif any(active):
        reason = "active_parameter_bounds"
    elif rank < n:
        reason = "rank_deficient_jacobian"
    elif dof <= 0:
        reason = "no_residual_degrees_of_freedom"
    elif (
        condition is None
        or not math.isfinite(condition)
        or condition > settings.maximum_condition_number
    ):
        reason = "ill_conditioned_jacobian"
    if condition is not None and not math.isfinite(condition):
        condition = None
    if reason is not None:
        return ParameterUncertainty(rank, dof, condition, None, None, reason)
    residual_variance = math.fsum(r * r for r in scaled) / dof
    covariance = (vt.T * (residual_variance / (singular * singular))) @ vt
    if not np.all(np.isfinite(covariance)):
        raise CalibrationError("Local uncertainty estimate is non-finite")
    values = tuple(tuple(float(x) for x in row) for row in covariance)
    std = tuple(
        require_finite(math.sqrt(float(x)), name="standard error") for x in np.diag(covariance)
    )
    return ParameterUncertainty(rank, dof, condition, values, std, None)


@dataclass(frozen=True, slots=True)
class ScipyLeastSquares:
    """TRF with linear loss, 3-point finite differences and Jacobian scaling.

    No multistart, global-optimum claim, outlier deletion, bound projection or
    implicit regularization penalty. Model evaluation failures remain explicit.
    """

    def solve(
        self,
        problem: CalibrationProblem,
        bounds: tuple[ParameterBound, ...],
        settings: CalibrationSettings,
        calibration_id: CalibrationRunId,
    ) -> CalibrationResult:
        if not isinstance(settings, CalibrationSettings) or not isinstance(
            calibration_id, CalibrationRunId
        ):
            raise CalibrationError("Typed calibration settings and run ID are required")
        require_tuple(bounds, ParameterBound, nonempty=True)
        if tuple(p.name for p in bounds) != problem.parameter_names:
            raise CalibrationError("Parameter names and order must match the calibration problem")
        count = len(problem.observed)
        if count == 0:
            raise CalibrationError("Calibration requires observations")
        observed = vector(problem.observed, count, "observed values")
        scales = vector(problem.scales, count, "quote scales")
        if any(scale <= 0 for scale in scales):
            raise CalibrationError("Quote residual scales must be positive")
        actual_evaluations = 0

        def predictions(parameters: State) -> State:
            try:
                return vector(problem.predict(parameters), count, "model predictions")
            except ParallaxError as error:
                raise CalibrationError("Calibration model evaluation failed") from error

        def objective(x: NDArray[np.float64]) -> NDArray[np.float64]:
            nonlocal actual_evaluations
            actual_evaluations += 1
            predicted = predictions(tuple(float(value) for value in x))
            residuals = tuple(
                require_finite((p - o) / s, name="scaled residual")
                for p, o, s in zip(predicted, observed, scales, strict=True)
            )
            return np.asarray(residuals, dtype=np.float64)

        # Verify both model-domain extremes before optimization; invalid bounds are
        # rejected rather than discovered only if the optimizer happens to visit them.
        predictions(tuple(b.lower for b in bounds))
        predictions(tuple(b.upper for b in bounds))
        result = least_squares(
            objective,
            np.asarray([b.initial for b in bounds]),
            bounds=([b.lower for b in bounds], [b.upper for b in bounds]),
            method="trf",
            jac="3-point",
            x_scale="jac",
            loss="linear",
            ftol=settings.function_tolerance,
            xtol=settings.parameter_tolerance,
            gtol=settings.gradient_tolerance,
            max_nfev=settings.max_evaluations,
        )
        fitted = vector(tuple(float(x) for x in result.x), len(bounds), "fitted parameters")
        predicted = predictions(fitted)
        residuals = tuple(
            require_finite(p - o, name="price residual")
            for p, o in zip(predicted, observed, strict=True)
        )
        scaled = tuple(
            require_finite(r / s, name="scaled residual")
            for r, s in zip(residuals, scales, strict=True)
        )
        rmse = require_finite(math.sqrt(math.fsum(r * r for r in residuals) / count), name="RMSE")
        scaled_rmse = require_finite(
            math.sqrt(math.fsum(r * r for r in scaled) / count), name="scaled RMSE"
        )
        active = tuple(int(x) for x in result.active_mask)
        converged = bool(result.success)
        uncertainty = _uncertainty(
            np.asarray(result.jac, dtype=np.float64), scaled, active, converged, settings
        )
        configuration_hash = content_hash(
            (bounds, settings, problem.model_name, problem.model_version, problem.input_hash)
        )
        return CalibrationResult(
            calibration_id,
            problem.model_name,
            problem.model_version,
            problem.input_hash,
            configuration_hash,
            CalibrationStatus.CONVERGED if converged else CalibrationStatus.FAILED,
            bounds,
            fitted,
            predicted,
            residuals,
            scaled,
            problem.value_unit,
            rmse,
            scaled_rmse,
            max(abs(r) for r in residuals),
            int(result.status),
            str(result.message),
            int(result.nfev),
            actual_evaluations,
            int(result.njev) if result.njev is not None else 0,
            require_finite(float(result.optimality), name="optimality"),
            active,
            uncertainty,
        )
