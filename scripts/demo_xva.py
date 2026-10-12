"""Repeatable synthetic signed XVA, actual central differences and movement residuals."""

import json

from parallax_risk.application.xva_examples import example
from parallax_risk.common.canonical import canonical_value


def report() -> dict[str, object]:
    research = example()
    return {
        "is_sample": True,
        "research": canonical_value(research),
        "total_adjustments": [
            canonical_value(v.result.total_adjustment) for v in research.valuations
        ],
        "interpretation": (
            "Unilateral/additive research approximations; not a bilateral replication price"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
