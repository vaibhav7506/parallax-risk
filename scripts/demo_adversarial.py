"""Emit canonical synthetic mutation/search/forensic evidence with retained misses."""

import json

from parallax_risk.application.adversarial_examples import example
from parallax_risk.common.canonical import canonical_value
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution


def main() -> None:
    print(
        json.dumps(
            canonical_value(
                {
                    "project": "Parallax Risk",
                    "release": "0.10.0",
                    "is_synthetic": True,
                    "model_approval": False,
                    "research": example(ScipyDifferentialEvolution()),
                }
            ),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
