"""Explicit synthetic prototype inputs; no market data or compliance attestation."""

import io
from dataclasses import replace
from datetime import date

import numpy as np

from parallax_risk.application.ccr import CcrService
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.exposure_examples import example_inputs
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import TradeId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.ccr.contracts import (
    AssetClass,
    ComparisonPolicy,
    MarginTerms,
    StandardizedInputs,
    SupervisoryParameters,
    SupervisoryTrade,
)
from parallax_risk.domain.exposure.statistics import profile
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.contracts import TimeGrid
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from tests.fixtures.deterministic import money


def parameters(**changes):
    return replace(SupervisoryParameters("Synthetic CRE52-inspired defaults; research"), **changes)


def policy(**changes):
    return replace(
        ComparisonPolicy(Currency.USD, money(1), 0.1, 1.0, 0.08, "Synthetic policy"), **changes
    )


def risk_trade(**changes):
    return replace(
        SupervisoryTrade(
            TradeId("fx"), AssetClass.FX, (Currency.EUR, Currency.USD), money(100), 1.0, 1.0
        ),
        **changes,
    )


def inputs(**changes):
    return replace(StandardizedInputs("cp/set", money(0), money(0), (risk_trade(),)), **changes)


def margin(**changes):
    return replace(
        MarginTerms(money(0), money(0), money(0), 10, "Explicit synthetic MPOR/NICA"), **changes
    )


def empirical(values=(10.0, 20.0, 5.0), times=(0.0, 0.25, 1.0)):
    positive = np.asarray([values, values], dtype=np.float64)
    return profile(positive, np.zeros_like(positive), times, (0.95,), Currency.USD)


def workflow_inputs(paths=2, *, daily=False):
    request, book, markets, run = example_inputs(paths)
    if daily:
        from datetime import timedelta

        dates = tuple(book.as_of + timedelta(days=i) for i in range(11))
        maturity = dates[-1]
        cp = book.counterparties[0]
        netting = cp.netting_sets[0]
        trade = netting.trades[0]
        book = replace(
            book,
            counterparties=(
                replace(
                    cp,
                    netting_sets=(
                        replace(
                            netting,
                            trades=(
                                replace(
                                    trade, instrument=replace(trade.instrument, maturity=maturity)
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    else:
        dates = (*markets.dates, date(2026, 1, 1))
    request = replace(
        request,
        grid=TimeGrid(tuple(year_fraction(book.as_of, d, DayCount.ACT_365_FIXED) for d in dates)),
    )
    return request, book, replace(markets, request=request, dates=dates), run


def service():
    logger = create_logger(stream=io.StringIO())
    return CcrService(
        ExposureService(MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger)
    )
