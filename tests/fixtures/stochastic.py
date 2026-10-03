"""Explicit synthetic Q-parameter recovery fixtures, never observed market data."""

from datetime import UTC, datetime

from parallax_risk.common.enums import Currency
from parallax_risk.common.identifiers import QuoteId
from parallax_risk.domain.calibration.contracts import ParameterBound
from parallax_risk.domain.calibration.problems import (
    BondOptionObservation,
    CallObservation,
    DiscountObservation,
    HestonCallProblem,
    HullWhiteBondOptionProblem,
    VasicekBondProblem,
)
from parallax_risk.domain.market.observations import SourceMetadata
from parallax_risk.domain.models.assets import Heston
from parallax_risk.domain.models.heston_pricing import heston_call
from parallax_risk.domain.models.rates import HullWhite, LinearForwardCurve, Vasicek

AS_OF = datetime(2025, 1, 1, tzinfo=UTC)
SOURCE = SourceMetadata("synthetic_phase3", "generated_from_declared_Q_parameters", AS_OF, True)


def vasicek_problem():
    model = Vasicek(0.35, 0.055, 0.025)
    observations = tuple(
        DiscountObservation(QuoteId(f"v{i}"), t, model.bond(0.02, t), SOURCE)
        for i, t in enumerate((0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0))
    )
    problem = VasicekBondProblem(Currency.USD, AS_OF, 0.02, observations)
    bounds = (
        ParameterBound("speed", 0.2, 0.03, 2.0),
        ParameterBound("level", 0.04, -0.1, 0.2),
        ParameterBound("volatility", 0.018, 0.0, 0.1),
    )
    return problem, bounds, (0.35, 0.055, 0.025)


def hull_white_problem():
    curve = LinearForwardCurve(0.03, 0.001)
    model = HullWhite(0.18, 0.012, curve)
    pairs = ((0.5, 2.0), (1.0, 3.0), (1.0, 5.0), (2.0, 5.0), (3.0, 8.0), (5.0, 10.0))
    observations = []
    for i, (expiry, maturity) in enumerate(pairs):
        strike = curve.discount(maturity) / curve.discount(expiry)
        observations.append(
            BondOptionObservation(
                QuoteId(f"hw{i}"),
                expiry,
                maturity,
                strike,
                model.bond_call(expiry, maturity, strike),
                SOURCE,
            )
        )
    problem = HullWhiteBondOptionProblem(Currency.USD, AS_OF, curve, tuple(observations))
    bounds = (ParameterBound("speed", 0.3, 0.01, 1.0), ParameterBound("volatility", 0.02, 0.0, 0.1))
    return problem, bounds, (0.18, 0.012)


def heston_problem():
    model = Heston(1.5, 0.045, 0.35, -0.65, 0.03, 0.01)
    observations = tuple(
        CallObservation(
            QuoteId(f"h{i}"),
            expiry,
            strike,
            heston_call(model, 100.0, 0.035, strike, expiry).value,
            SOURCE,
        )
        for i, (expiry, strike) in enumerate(
            (
                (0.25, 85.0),
                (0.25, 100.0),
                (0.25, 115.0),
                (0.75, 85.0),
                (0.75, 100.0),
                (0.75, 115.0),
                (1.5, 85.0),
                (1.5, 100.0),
                (1.5, 115.0),
                (3.0, 85.0),
                (3.0, 100.0),
                (3.0, 115.0),
            )
        )
    )
    problem = HestonCallProblem(Currency.USD, AS_OF, 100.0, 0.03, 0.01, observations)
    bounds = (
        ParameterBound("speed", 1.2, 0.3, 4.0),
        ParameterBound("variance_level", 0.05, 0.01, 0.12),
        ParameterBound("vol_of_variance", 0.3, 0.1, 0.7),
        ParameterBound("correlation", -0.5, -0.9, 0.5),
        ParameterBound("initial_variance", 0.04, 0.01, 0.1),
    )
    return problem, bounds, (1.5, 0.045, 0.35, -0.65, 0.035)
