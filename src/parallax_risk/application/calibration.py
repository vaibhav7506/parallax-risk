"""Injected calibration port and run-correlated workflow, without HTTP or persistence."""

from dataclasses import dataclass
from typing import Protocol

from parallax_risk.application.context import RunContext
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.domain.calibration.contracts import (
    CalibrationProblem,
    CalibrationResult,
    CalibrationSettings,
    ParameterBound,
)


class CalibrationSolver(Protocol):
    def solve(
        self,
        problem: CalibrationProblem,
        bounds: tuple[ParameterBound, ...],
        settings: CalibrationSettings,
        calibration_id: CalibrationRunId,
    ) -> CalibrationResult: ...


@dataclass(frozen=True, slots=True)
class CalibrationRunResult:
    context: RunContext
    calibration: CalibrationResult


@dataclass(frozen=True, slots=True)
class CalibrationService:
    solver: CalibrationSolver
    logger: WorkflowLogger

    def calibrate(
        self,
        problem: CalibrationProblem,
        bounds: tuple[ParameterBound, ...],
        settings: CalibrationSettings,
        calibration_id: CalibrationRunId,
        run: RunContext,
    ) -> CalibrationRunResult:
        self.logger.event("calibration_started", run_id=str(run.run_id), outcome="started")
        try:
            result = self.solver.solve(problem, bounds, settings, calibration_id)
        except ParallaxError as error:
            self.logger.event(
                "calibration_failed",
                run_id=str(run.run_id),
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event(
            "calibration_completed", run_id=str(run.run_id), outcome=result.status.value
        )
        return CalibrationRunResult(run, result)
