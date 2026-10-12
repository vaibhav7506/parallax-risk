"""Reject malformed financial evidence rather than clipping or silently repairing it."""

from dataclasses import replace

import numpy as np
import pytest

from parallax_risk.application.xva_revaluation import FactorMove
from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import ParallaxError
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import exposure_at_default
from parallax_risk.domain.xva.calculators import (
    credit_integral,
    funding_integral,
    sampled_credit_loss,
)
from parallax_risk.domain.xva.contracts import ComponentKind, FundingSpreadCurve
from parallax_risk.domain.xva.risk import FactorKind, RiskFactor, attribute, sensitivity
from tests.fixtures.deterministic import money
from tests.fixtures.xva import curve, funding, margin, own, result


@pytest.mark.parametrize(
    "times,spreads",
    [
        ([0.0, 1.0], (0.01,)),
        ((0.0,), ()),
        ((0.0, 1.0), [0.01]),
        ((0.0, 1.0), ()),
        ((0.0, 1.0), (-0.01,)),
        ((0.0, 1.0), (float("nan"),)),
        ((0.0, 1.0), (True,)),
        ((0.1, 1.0), (0.01,)),
        ((0.0, 0.0), (0.01,)),
    ],
)
def test_funding_curve_invalid(times, spreads):
    with pytest.raises(ParallaxError):
        FundingSpreadCurve(times, spreads)


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "USD"},
        {"source": " "},
        {"posted_initial_margin": (-1.0, 0.0, 0.0)},
        {"posted_initial_margin": (float("inf"), 0.0, 0.0)},
        {"posted_initial_margin": [0.0, 0.0, 0.0]},
        {"times": (0.0, 1.0, 1.0)},
    ],
)
def test_invalid_margin(changes):
    with pytest.raises(ParallaxError):
        margin(**changes)


def test_funding_own_and_quadrature_guards():
    for changes in (
        {"borrowing": None},
        {"lending": None},
        {"margin": None},
        {"include_lending_benefit": 1},
    ):
        with pytest.raises(ParallaxError):
            replace(funding(), **changes)
    for changes in ({"hazard": None}, {"recovery": None}):
        with pytest.raises(ParallaxError):
            replace(own(), **changes)
    for time in (-1, 3, float("nan"), True):
        with pytest.raises(ParallaxError):
            funding().borrowing.spread(time)
    assert funding().borrowing.spread(2.0) == 0.01
    with pytest.raises(ParallaxError):
        funding_integral(
            (0.0, 1.0), (1.0, 1.0), curve(day_count=DayCount.ACT_360), funding().borrowing
        )
    with pytest.raises(ParallaxError):
        funding_integral((0.0, 1.0), (1.0, 1.0), curve(), None)
    with pytest.raises(ParallaxError):
        credit_integral((0.0, 1.0), (1.0, 1.0), curve(), None, RecoveryAssumption(0.4))
    with pytest.raises(ParallaxError):
        funding_integral(
            (0.0, 2.0), (1e308, 1e308), curve(), FundingSpreadCurve((0.0, 2.0), (1e308,))
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "CVA"},
        {"adjustment": None},
        {"contributions": [-1.0]},
        {"contributions": (float("nan"),)},
        {"input_hash": "bad"},
        {"methodology": " "},
        {"contribution_labels": ()},
        {"contribution_labels": ("only",)},
        {"contribution_labels": (" ", "ok")},
        {"adjustment": money(-1)},
        {"adjustment": money(1), "contributions": (0.5, 0.5)},
    ],
)
def test_component_invalid(changes):
    with pytest.raises(ParallaxError):
        replace(result().component(ComponentKind.CVA), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "USD"},
        {"components": ()},
        {"components": []},
        {"funding_cost": None},
        {"funding_cost": money(-1)},
        {"funding_benefit": money(1, Currency.EUR)},
        {"funding_cost": money(5)},
        {"input_hash": "bad"},
        {"attribution": (("a",),)},
        {"attribution": (("a", "x"), ("a", "y"))},
        {"attribution": (("a", " "),)},
        {"assumptions": ()},
        {"assumptions": (" ",)},
        {"model_version": " "},
    ],
)
def test_result_invalid(changes):
    with pytest.raises(ParallaxError):
        replace(result(), **changes)


def foreign_result():
    r = result()
    return replace(
        r,
        currency=Currency.EUR,
        components=tuple(
            replace(c, adjustment=money(c.adjustment.amount, Currency.EUR)) for c in r.components
        ),
        funding_cost=money(r.funding_cost.amount, Currency.EUR),
        funding_benefit=money(r.funding_benefit.amount, Currency.EUR),
    )


def test_component_order_currency_and_lookup():
    r = result()
    for components in (tuple(reversed(r.components)), foreign_result().components):
        with pytest.raises(ParallaxError):
            replace(r, components=components)
    with pytest.raises(ParallaxError):
        r.component("OTHER")
    with pytest.raises(ParallaxError, match="component evidence"):
        replace(r, components=(replace(r.components[0], input_hash="f" * 64), *r.components[1:]))


@pytest.mark.parametrize(
    "changes",
    [
        {"default_times": ()},
        {"bucket_times": ()},
        {"positive_exposures": (-1.0,)},
        {"default_times": (None,)},
        {"default_times": (None,), "bucket_times": (None,)},
        {"default_times": (-1.0,)},
        {"default_times": (float("nan"),)},
        {"default_times": (True,)},
        {"bucket_times": (2.0,)},
    ],
)
def test_sampled_loss_invalid(changes):
    ead = exposure_at_default(
        np.array([[1.0, 2.0, 3.0]], dtype=np.float64), (0.0, 1.0, 2.0), (0.5,)
    )
    with pytest.raises(ParallaxError):
        sampled_credit_loss(
            (0.0, 1.0, 2.0), replace(ead, **changes), curve(), RecoveryAssumption(0.4)
        )


def test_sampled_types_and_hazard_horizon():
    for ead, recovery in ((None, RecoveryAssumption(0.4)), (None, None)):
        with pytest.raises(ParallaxError):
            sampled_credit_loss((0.0, 1.0, 2.0), ead, curve(), recovery)
    with pytest.raises(ParallaxError):
        credit_integral(
            (0.0, 2.0),
            (1.0, 1.0),
            curve(),
            PiecewiseHazardCurve((0.0, 1.0), (0.1,)),
            RecoveryAssumption(0.4),
        )


@pytest.mark.parametrize(
    "args",
    [
        ("fx", "fx"),
        (FactorKind.FX, " "),
        (FactorKind.FX, "fx", "other"),
        (FactorKind.CORRELATION, "fx"),
        (FactorKind.CORRELATION, "fx", "fx"),
    ],
)
def test_risk_factor_invalid(args):
    with pytest.raises(ParallaxError):
        RiskFactor(*args)


@pytest.mark.parametrize("bump", [0, -1, float("nan"), True, 5e-324])
def test_central_bump_invalid(bump):
    with pytest.raises(ParallaxError):
        sensitivity(RiskFactor(FactorKind.FX, "fx"), bump, "USD per FX", lambda _: result())


def test_sensitivity_invalid_results_and_inputs():
    f = RiskFactor(FactorKind.FX, "fx")
    for factor, callback in (
        (None, lambda _: result()),
        (f, lambda _: None),
        (f, lambda _: result()),
        (f, lambda x: result() if x == 0 else foreign_result()),
    ):
        with pytest.raises(ParallaxError):
            sensitivity(factor, 0.01, "USD per FX", callback)


def test_attribution_rejects_malformed_ladders_and_reports_empty_residual():
    r = result()
    for ladder in ((("a", r), ("a", r)), (("a",),), (("a", None),), (("a", foreign_result()),)):
        with pytest.raises(ParallaxError):
            attribute(r, ladder, r)
    for base, actual in ((None, r), (r, None), (r, foreign_result())):
        with pytest.raises(ParallaxError):
            attribute(base, (), actual)
    empty = attribute(r, (), r)
    assert empty.steps == () and empty.explained_change == empty.unexplained_change == 0


def test_factor_move_validation_and_duplicate_preflight():
    from tests.fixtures.xva import experiment, revaluation

    f = RiskFactor(FactorKind.FX, "fx")
    for args in ((" ", f, 1.0), ("a", None, 1.0), ("a", f, float("inf"))):
        with pytest.raises(ParallaxError):
            FactorMove(*args)
    e = experiment(paths=4)
    with pytest.raises(ParallaxError):
        revaluation().attribute(e, (FactorMove("a", f, 0.01), FactorMove("a", f, 0.02)), e)
