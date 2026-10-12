"""Independent hand inputs and actual synthetic production revaluation factories."""

import io
import math
from dataclasses import replace

import numpy as np

from parallax_risk.application.exposure_examples import example_credit, example_inputs
from parallax_risk.application.xva import AdditiveXvaCalculator, XvaService
from parallax_risk.application.xva_revaluation import XvaExperiment, XvaRevaluation
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.identifiers import CurveId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import profile
from parallax_risk.domain.market.curves.interpolation import ExtrapolationPolicy, InterpolationKind
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.xva.calculators import calculate
from parallax_risk.domain.xva.contracts import (
    FundingSpreadCurve,
    FundingTerms,
    MarginProfile,
    OwnCredit,
)
from tests.fixtures.deterministic import VALUATION
from tests.fixtures.exposure import service


def curve(times=(0.0, 1.0, 2.0), rate=0.0, **changes):
    return replace(
        DiscountCurve(
            CurveId("xva-discount"),
            Currency.USD,
            VALUATION,
            DayCount.ACT_365_FIXED,
            times,
            tuple(math.exp(-rate * t) for t in times),
            InterpolationKind.LOG_LINEAR,
            ExtrapolationPolicy.ERROR,
        ),
        **changes,
    )


def exposure(times=(0.0, 1.0, 2.0), positive=None, negative=None, **changes):
    positive = positive if positive is not None else (100.0,) * len(times)
    negative = negative if negative is not None else (50.0,) * len(times)
    return replace(
        profile(
            np.array([positive, positive], dtype=np.float64),
            np.array([negative, negative], dtype=np.float64),
            times,
            (0.95,),
            Currency.USD,
        ),
        **changes,
    )


def funding(horizon=2.0, benefit=True):
    spreads = tuple(FundingSpreadCurve((0.0, horizon), (s,)) for s in (0.01, 0.005, 0.02))
    return FundingTerms(*spreads, benefit)


def own(horizon=2.0):
    return OwnCredit(PiecewiseHazardCurve((0.0, horizon), (0.1,)), RecoveryAssumption(0.4))


def margin(times=(0.0, 1.0, 2.0), **changes):
    return replace(
        MarginProfile(
            Currency.USD, times, (10.0,) * len(times), "Synthetic externally supplied segregated IM"
        ),
        **changes,
    )


def result(**changes):
    arguments = {
        "profile": exposure(),
        "discount": curve(),
        "counterparty": PiecewiseHazardCurve((0.0, 2.0), (0.2,)),
        "recovery": RecoveryAssumption(0.4),
        "own": own(),
        "funding": funding(),
        "margin": margin(),
    }
    return calculate(**(arguments | changes))


def experiment(paths=16, kind=0):
    request, book, markets, run = example_inputs(paths)
    times = request.grid.times
    return XvaExperiment(
        request,
        book,
        markets,
        (),
        (example_credit(request, book)[kind],),
        own(times[-1]),
        curve(times, 0.03),
        funding(times[-1]),
        (margin(times),),
        run,
    )


def revaluation():
    logger = create_logger(stream=io.StringIO())
    return XvaRevaluation(service(), XvaService(AdditiveXvaCalculator(), logger))
