"""Synthetic Q rates/FX/spread scenarios; intentionally no market-data calibration."""

import io
from dataclasses import replace
from datetime import date
from decimal import Decimal

from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import CsaId, NettingSetId
from parallax_risk.common.logging import create_logger
from parallax_risk.common.time import year_fraction
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario, FxBinding, RateBinding
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.rates import Vasicek
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.contracts import (
    ProcessComponent,
    Scheme,
    SimulationRequest,
    TimeGrid,
)
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.random import SequenceSpec, StreamKey
from tests.fixtures.deterministic import VALUATION, YEAR_ONE, money
from tests.fixtures.portfolio import account, csa, netting, portfolio, trade


def rate_component(name="usd", currency=Currency.USD, volatility=0.02):
    return ProcessComponent(
        name, Vasicek(0.4, 0.03, volatility), (0.03,), Scheme.EXACT, ("decimal_annual_rate",), "Q"
    )


def request(paths=8, batch=4, dates=(VALUATION, date(2025, 7, 1)), extra=()):
    return SimulationRequest(
        (rate_component(), *extra),
        TimeGrid(tuple(year_fraction(VALUATION, d, DayCount.ACT_365_FIXED) for d in dates)),
        paths,
        batch,
        SequenceSpec(StreamKey(42)),
    )


def markets(req, dates=(VALUATION, date(2025, 7, 1)), **changes):
    return replace(
        ConditionalMarketScenario(
            req,
            dates,
            (date(2025, 7, 1), YEAR_ONE, date(2027, 1, 1)),
            (RateBinding(Currency.USD, "usd", ("USD-SYNTH-1Y",)),),
        ),
        **changes,
    )


def service(engine=None):
    logger = create_logger(stream=io.StringIO())
    return ExposureService(
        engine or MonteCarloEngine(), PortfolioService(DiscountingEngine(), logger), logger
    )


def fx_request(paths=32, batch=16, dates=(VALUATION, date(2025, 7, 1)), spread_vol=0.6):
    req = request(
        paths,
        batch,
        dates,
        extra=(
            rate_component("eur", Currency.EUR, 0),
            ProcessComponent(
                "fx", GeometricBrownianMotion(0, 0.3), (1.1,), Scheme.EXACT, ("USD/EUR",), "Q"
            ),
            ProcessComponent(
                "credit",
                GeometricBrownianMotion(0, spread_vol),
                (0.12,),
                Scheme.EXACT,
                ("decimal_annual_spread",),
                "Q",
            ),
        ),
    )
    return replace(
        req,
        components=(replace(req.components[0], process=Vasicek(0.4, 0.03, 0)), *req.components[1:]),
    )


def fx_markets(req, dates=(VALUATION, date(2025, 7, 1))):
    return markets(
        req,
        dates,
        rates=(RateBinding(Currency.USD, "usd"), RateBinding(Currency.EUR, "eur")),
        fx=(FxBinding(Currency.EUR, Currency.USD, "fx"),),
    )


def fx_book():
    record = trade(
        instrument=FxForward(
            money(100, Currency.EUR), Currency.USD, Decimal("1.1"), YEAR_ONE, FxDirection.BUY_BASE
        )
    )
    cp = portfolio().counterparties[0]
    return portfolio(counterparties=(replace(cp, netting_sets=(netting(trades=(record,)),)),))


def collateral_book(lag=1):
    book = portfolio()
    cp = book.counterparties[0]
    scope = netting(
        csa=csa(
            receive_threshold=money(0),
            post_threshold=money(0),
            minimum_transfer_amount=money(0),
            settlement_lag_days=lag,
        ),
        trades=(trade(),),
    )
    return portfolio(counterparties=(replace(cp, netting_sets=(scope,)),)), account()


def second_scope(book: PortfolioSnapshot):
    cp = book.counterparties[0]
    first = cp.netting_sets[0]
    second = netting(
        netting_set_id=NettingSetId("other"),
        trades=(trade("other", -100),),
        csa=csa(csa_id=CsaId("other")) if first.csa else None,
    )
    return replace(book, counterparties=(replace(cp, netting_sets=(first, second)),))
