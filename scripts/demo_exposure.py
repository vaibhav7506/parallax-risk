"""Repeatable synthetic exposure/default summaries; explicitly no CVA or regulatory EAD."""

import json

from parallax_risk.application.exposure_examples import example, example_credit, example_inputs
from parallax_risk.common.canonical import canonical_value


def report() -> dict[str, object]:
    request, book, market, run = example_inputs()
    results = example()
    return {
        "is_sample": True,
        "request": canonical_value(request),
        "portfolio": canonical_value(book),
        "markets": canonical_value(market),
        "run": canonical_value(run),
        "credit_scenarios": canonical_value(example_credit(request, book)),
        "results": [
            {
                "context": canonical_value(r.context),
                "simulation": canonical_value(r.simulation),
                "portfolio_hash": r.portfolio_hash,
                "market_scenario_hash": r.market_scenario_hash,
                "market_path_digest": r.market_path_digest,
                "positive_path_hash": r.positive_paths.hash,
                "negative_path_hash": r.negative_paths.hash,
                "times": r.total_profile.times,
                "EE": r.total_profile.expected_exposure,
                "ENE": r.total_profile.expected_negative_exposure,
                "EPE": r.total_profile.expected_positive_exposure,
                "quantiles": r.total_profile.quantiles,
                "PFE": r.total_profile.potential_future_exposure.array.tolist(),
                "baseline_survival": r.counterparties[0].baseline_survival,
                "scenario_survival": r.counterparties[0].scenario_survival,
                "default_comparison": canonical_value(r.counterparties[0].default_comparison),
                "assumptions": r.assumptions,
            }
            for r in results
        ],
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
