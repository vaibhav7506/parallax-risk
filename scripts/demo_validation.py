"""Emit canonical labelled synthetic Phase 9 validation evidence."""

import json

from parallax_risk.application.validation_examples import example
from parallax_risk.common.canonical import canonical_value
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares


def main() -> None:
    print(
        json.dumps(
            canonical_value(
                {
                    "project": "Parallax Risk",
                    "is_synthetic": True,
                    "model_approval": False,
                    "release": "0.9.0",
                    "validation": example(ScipyLeastSquares()),
                }
            ),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
