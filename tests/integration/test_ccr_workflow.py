"""Actual production exposure workflow, legal isolation, collateral and adapter evidence."""

from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

import pytest

from parallax_risk.application.ccr import ScopeMargin
from parallax_risk.common.canonical import canonical_value
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.identifiers import NettingSetId, TradeId
from parallax_risk.domain.portfolio.csa import CollateralDirection
from tests.fixtures.ccr import margin, parameters, policy, service, workflow_inputs
from tests.fixtures.deterministic import money
from tests.fixtures.portfolio import account, csa, trade


def test_replay_batch_independence_and_distinct_netting_sets():
    request, book, markets, run = workflow_inputs(paths=4)
    first = service().run(request, book, markets, run, parameters(), policy())
    changed = replace(request, batch_size=1)
    second = service().run(
        changed, book, replace(markets, request=changed), run, parameters(), policy()
    )
    assert first.scopes[0].comparison == second.scopes[0].comparison
    assert first.scopes[0].positive_path_hash == second.scopes[0].positive_path_hash
    cp = book.counterparties[0]
    ns = cp.netting_sets[0]
    opposite = replace(
        ns,
        netting_set_id=NettingSetId("other-set"),
        trades=(replace(ns.trades[0], trade_id=TradeId("opposite"), quantity=Decimal(-1)),),
    )
    split = replace(book, counterparties=(replace(cp, netting_sets=(ns, opposite)),))
    result = service().run(request, split, markets, run, parameters(), policy())
    assert len(result.scopes) == 2 and result.standardized_ead.amount > 0
    assert result.standardized_ead == sum(
        (s.comparison.standardized.ead for s in result.scopes), money(0)
    )
    assert result.challenger_ead == sum(
        (s.comparison.challenger.ead for s in result.scopes), money(0)
    )
    assert canonical_value(result)["assumptions"]


def margin_book():
    request, book, markets, run = workflow_inputs(daily=True)
    cp = book.counterparties[0]
    ns = cp.netting_sets[0]
    terms = csa(
        receive_threshold=money(0),
        post_threshold=money(0),
        minimum_transfer_amount=money(0),
        eligible_collateral=(csa().eligible(Currency.USD),),
        settlement_lag_days=0,
        margin_period_of_risk_days=0,
    )
    book = replace(book, counterparties=(replace(cp, netting_sets=(replace(ns, csa=terms),)),))
    return request, book, markets, run


def test_actual_margin_paths_explicit_business_day_and_nica_inputs():
    request, book, markets, run = margin_book()
    result = service().run(
        request,
        book,
        markets,
        run,
        parameters(),
        policy(),
        accounts=(account(),),
        margins=(ScopeMargin(NettingSetId("synthetic-set"), margin()),),
    )
    scope = result.scopes[0]
    assert scope.account_hashes == (account().account_hash,)
    assert scope.comparison.standardized.unmargined_ead_cap is not None
    assert scope.comparison.challenger.expected_exposure == tuple(0 for _ in markets.dates)
    assert scope.comparison.challenger.ead == money(0)
    cp = book.counterparties[0]
    unmargin_book = replace(
        book, counterparties=(replace(cp, netting_sets=(replace(cp.netting_sets[0], csa=None),)),)
    )
    unmargin_result = service().run(request, unmargin_book, markets, run, parameters(), policy())
    assert unmargin_result.challenger_ead.amount > result.challenger_ead.amount


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_ledger",
        "missing_ledger",
        "extra_margin",
        "missing_margin",
        "mismatch_threshold",
        "non_daily",
        "post_only",
    ],
)
def test_margin_scope_and_policy_reject(kind):
    request, book, markets, run = margin_book()
    ledgers = (account(),)
    margins = (ScopeMargin(NettingSetId("synthetic-set"), margin()),)
    if kind == "duplicate_ledger":
        ledgers *= 2
    elif kind == "missing_ledger":
        ledgers = ()
    elif kind == "extra_margin":
        margins *= 2
    elif kind == "missing_margin":
        margins = ()
    elif kind == "mismatch_threshold":
        margins = (replace(margins[0], terms=margin(threshold=money(1))),)
    else:
        cp = book.counterparties[0]
        ns = cp.netting_sets[0]
        terms = (
            replace(ns.csa, frequency_days=2)
            if kind == "non_daily"
            else replace(ns.csa, direction=CollateralDirection.POST_ONLY)
        )
        book = replace(book, counterparties=(replace(cp, netting_sets=(replace(ns, csa=terms),)),))
    with pytest.raises(ParallaxError):
        service().run(
            request, book, markets, run, parameters(), policy(), accounts=ledgers, margins=margins
        )


@pytest.mark.parametrize(
    "kind",
    [
        "invalid_input",
        "currency",
        "seed",
        "request",
        "scope_currency",
        "inactive",
        "empty",
        "product",
        "budget",
    ],
)
def test_workflow_invalid_boundaries(kind):
    request, book, markets, run = workflow_inputs()
    pol = policy()
    budget = 256 * 1024 * 1024
    if kind == "invalid_input":
        request = None
    elif kind == "currency":
        pol = policy(currency=Currency.EUR, absolute_tolerance=money(1, Currency.EUR))
    elif kind == "seed":
        run = replace(run, seed=1)
    elif kind == "request":
        request = replace(request, path_count=4)
    elif kind == "empty":
        book = replace(book, counterparties=())
    elif kind == "budget":
        budget = 1
    else:
        cp = book.counterparties[0]
        ns = cp.netting_sets[0]
        if kind == "scope_currency":
            ns = replace(ns, reporting_currency=Currency.EUR)
        elif kind == "inactive":
            ns = replace(
                ns,
                trades=(
                    replace(
                        ns.trades[0],
                        termination_date=book.as_of,
                        termination_reason="Synthetic closed",
                    ),
                ),
            )
        else:
            ns = replace(ns, trades=(trade(),))
        book = replace(book, counterparties=(replace(cp, netting_sets=(ns,)),))
    with pytest.raises(ParallaxError):
        service().run(request, book, markets, run, parameters(), pol, maximum_output_bytes=budget)


@pytest.mark.parametrize(
    "field",
    [
        "portfolio_hash",
        "context",
        "market_scenario_hash",
        "initial_account_hashes",
        "simulation",
        "dates",
        "total_profile",
        "positive_paths",
    ],
)
def test_injected_exposure_stale_evidence_reject(field):
    request, book, markets, run = workflow_inputs()
    workflow = service()
    original = type(workflow.exposure).run

    def stale(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        values = {
            "portfolio_hash": "b" * 64,
            "context": replace(run, seed=1),
            "market_scenario_hash": "c" * 64,
            "initial_account_hashes": ("d" * 64,),
            "simulation": replace(result.simulation, request_hash="e" * 64),
            "dates": result.dates[:-1],
            "total_profile": replace(result.total_profile, paths=1),
            "positive_paths": result.negative_paths.__class__.from_array(
                result.positive_paths.array[:, :-1, :]
            ),
        }
        return replace(result, **{field: values[field]})

    with patch.object(type(workflow.exposure), "run", stale), pytest.raises(ParallaxError):
        workflow.run(request, book, markets, run, parameters(), policy())


def test_scope_margin_requires_typed_values():
    with pytest.raises(ParallaxError):
        ScopeMargin("untyped", margin())
    with pytest.raises(ParallaxError):
        ScopeMargin(NettingSetId("set"), None)


def test_labelled_synthetic_example_and_report():
    import runpy

    from parallax_risk.application.ccr_examples import example

    result = example(paths=2)
    assert str(result.context.run_id) == "synthetic-phase8"
    assert result.scopes[0].comparison.standardized.methodology.endswith("v0.8.0")
    namespace = runpy.run_path("scripts/demo_ccr.py")
    namespace["report"].__globals__["example"] = lambda: result
    report = namespace["report"]()
    assert report["is_sample"] and not report["regulatory_compliance"]
