"""Reproduce the explicitly synthetic Phase 3 instrument calibration example."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from parallax_risk.application.calibration import CalibrationService
from parallax_risk.application.calibration_inputs import CalibrationRequest
from parallax_risk.application.config import Settings
from parallax_risk.application.context import create_run_context
from parallax_risk.common.canonical import canonical_value
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Read strict inputs, fit actual SciPy objectives, emit traceable JSON and safe logs."""
    sample = json.loads((ROOT / "data/sample/phase3_calibration.json").read_text(encoding="utf-8"))
    service = CalibrationService(ScipyLeastSquares(), create_logger("INFO", stream=sys.stderr))
    outputs = []
    for case in sample["cases"]:
        request = CalibrationRequest.model_validate(case["request"])
        problem, bounds, settings, calibration_id = request.to_domain()
        run = create_run_context(
            Settings(),
            run_id=RiskRunId(str(calibration_id)),
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            seed=0,
        )
        result = service.calibrate(problem, bounds, settings, calibration_id, run)
        result.calibration.require_converged()
        outputs.append(
            {
                "generating_parameters": case["generating_parameters"],
                "result": canonical_value(result),
            }
        )
    print(
        json.dumps(
            {"project": "Parallax Risk", "is_synthetic": True, "calibrations": outputs},
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
