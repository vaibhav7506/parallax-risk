"""Run synthetic Phase 4 research experiments and emit replayable JSON."""

import json

from parallax_risk.application.simulation_examples import (
    convergence_experiment,
    moment_experiment,
    variance_experiment,
)
from parallax_risk.common.canonical import canonical_value


def main() -> None:
    report = {
        "project": "Parallax Risk",
        "is_synthetic": True,
        "moments": canonical_value(moment_experiment()),
        "variance_reduction": canonical_value(variance_experiment()),
        "convergence": canonical_value(convergence_experiment()),
    }
    print(json.dumps(report, indent=2, allow_nan=False, sort_keys=True))


if __name__ == "__main__":
    main()
