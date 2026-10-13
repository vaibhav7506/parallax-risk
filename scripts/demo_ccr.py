"""Repeatable synthetic SA-CCR-inspired versus actual IMM challenger research report."""

import json

from parallax_risk.application.ccr_examples import example
from parallax_risk.common.canonical import canonical_value


def report() -> dict[str, object]:
    return {
        "is_sample": True,
        "regulatory_compliance": False,
        "research": canonical_value(example()),
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
