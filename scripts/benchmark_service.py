"""Measured synthetic profiling, equivalent-history optimization and compute scaling."""

import cProfile
import io
import json
import platform
import pstats
import time
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from parallax_risk.application.service_examples import commands
from parallax_risk.application.wire import document
from parallax_risk.application.workflows import Operation
from parallax_risk.common.identifiers import CollateralMovementId, TradeId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.domain.portfolio.collateral import (
    CollateralMovement,
    collateral_value,
    validate_account,
)
from parallax_risk.infrastructure.service_composition import make_workflows


def compute(paths: int) -> str:
    workflow = make_workflows(create_logger(stream=io.StringIO()))
    return document(workflow.execute(commands(paths)[Operation.XVA])).hash


def measure(function):
    tracemalloc.start()
    start = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"seconds": elapsed, "python_tracemalloc_peak_bytes": peak}, result


def main() -> None:
    target = Path("artifacts/local/phase12")
    target.mkdir(parents=True, exist_ok=True)
    workflow = make_workflows(create_logger(stream=io.StringIO()))
    case = commands(4)[Operation.PORTFOLIO]
    account = case.accounts[0]
    csa = case.book.counterparties[0].netting_sets[0].csa
    movements = tuple(
        CollateralMovement(
            CollateralMovementId(str(i)),
            account.opening_date + timedelta(days=i),
            account.opening_date + timedelta(days=i),
            Money(Decimal(1 if i % 2 == 0 else -1), csa.currency),
        )
        for i in range(365)
    )
    ledger = replace(account, movements=movements)

    def original():
        for day in sorted({ledger.opening_date, *(m.settlement_date for m in ledger.movements)}):
            collateral_value(ledger.balances(day), csa, case.market)

    before, _ = measure(original)
    after, _ = measure(lambda: validate_account(ledger, csa, case.market))
    # Large portfolio is deterministic pricing, distinct from simulated-tail evidence.
    scope = case.book.counterparties[0].netting_sets[0]
    book = replace(
        case.book,
        counterparties=(
            replace(
                case.book.counterparties[0],
                netting_sets=(
                    replace(
                        scope,
                        trades=tuple(
                            replace(scope.trades[0], trade_id=TradeId("trade-" + str(i)))
                            for i in range(512)
                        ),
                    ),
                ),
            ),
        ),
    )
    large, result = measure(lambda: workflow.execute(replace(case, book=book)))
    profile = cProfile.Profile()
    profile.enable()
    result_xva = compute(16)
    profile.disable()
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(30)
    (target / "profile-service.txt").write_text(stream.getvalue(), encoding="utf-8")
    parallel = {}
    hashes = []
    for name, pool_type in (
        ("serial", None),
        ("thread_2", ThreadPoolExecutor),
        ("process_2", ProcessPoolExecutor),
    ):
        start = time.perf_counter()
        if pool_type is None:
            values = tuple(compute(8) for _ in range(4))
        else:
            with pool_type(2) as pool:
                values = tuple(pool.map(compute, (8,) * 4))
        parallel[name] = {
            "seconds_including_pool_startup": time.perf_counter() - start,
            "equal_financial_results": len(set(values)) == 1,
        }
        hashes.extend(values)
    if len(set(hashes)) != 1:
        raise RuntimeError("Parallel execution changed deterministic outputs")
    report = {
        "project": "Parallax Risk",
        "is_synthetic": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "history_movements": 365,
        "history_original": before,
        "history_cumulative": after,
        "history_speed_ratio": before["seconds"] / after["seconds"],
        "large_portfolio_trades": 512,
        "large_portfolio": large,
        "large_portfolio_result_hash": document(result).hash,
        "profile_xva_hash": result_xva,
        "parallel_four_independent_jobs": parallel,
        "limitations": [
            "One local observation, no portable performance guarantee",
            "Tracemalloc tracks Python allocations, not total native/RSS memory",
            "Parallel jobs repeat one synthetic case with explicit addressed streams",
            "Before code is the retained original historical balance reconstruction",
        ],
    }
    (target / "benchmark-service.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
