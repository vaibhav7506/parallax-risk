"""Real solver through injected application service, safe logs and run lineage."""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from parallax_risk.application.calibration import CalibrationService
from parallax_risk.application.config import Settings
from parallax_risk.application.context import create_run_context
from parallax_risk.common.errors import CalibrationError
from parallax_risk.common.identifiers import CalibrationRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.calibration.contracts import CalibrationSettings
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from tests.fixtures.stochastic import vasicek_problem


def test_service_run_metadata_and_safe_logging():
    problem, bounds, _ = vasicek_problem()
    stream = io.StringIO()
    run = create_run_context(Settings())
    service = CalibrationService(ScipyLeastSquares(), create_logger("INFO", stream=stream))
    output = service.calibrate(
        problem, bounds, CalibrationSettings(), CalibrationRunId("integration"), run
    )
    assert output.context == run and output.calibration.input_data_hash == problem.input_hash
    assert output.calibration.calibration_id == CalibrationRunId("integration")
    assert (
        "calibration_started" in stream.getvalue() and "calibration_completed" in stream.getvalue()
    )
    assert str(run.run_id) in stream.getvalue() and "fitted_parameters" not in stream.getvalue()
    with pytest.raises(CalibrationError):
        service.calibrate(
            problem, tuple(reversed(bounds)), CalibrationSettings(), CalibrationRunId("bad"), run
        )
    assert "calibration_failed" in stream.getvalue()


def test_synthetic_example_uses_production_workflow():
    root = Path(__file__).resolve().parents[2]
    output = subprocess.run(
        [sys.executable, str(root / "scripts/demo_calibration.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=90,
    )
    payload = json.loads(output.stdout)
    assert payload["project"] == "Parallax Risk" and payload["is_synthetic"] is True
    assert len(payload["calibrations"]) == 3
    for case in payload["calibrations"]:
        result = case["result"]["calibration"]
        assert result["status"] == "converged" and result["rmse"] < 1e-8
        assert result["fitted_parameters"] == pytest.approx(case["generating_parameters"], abs=3e-5)
    assert "calibration_completed" in output.stderr
