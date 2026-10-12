"""Independent credit/funding targets, convergence and justified sign properties."""

import math
from dataclasses import replace

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError, NumericalError
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import exposure_at_default
from parallax_risk.domain.xva.calculators import (
    credit_integral,
    funding_integral,
    sampled_credit_loss,
)
from parallax_risk.domain.xva.contracts import ComponentKind, FundingSpreadCurve
from tests.fixtures.xva import curve, exposure, funding, margin, own, result


def test_constant_exposure_exact_default_and_funding_targets():
    r = result()
    cva = 60 * (-math.expm1(-0.4))
    dva = 30 * (-math.expm1(-0.2))
    targets = (-cva, dva, -1.5, -0.4)
    for kind, target in zip(ComponentKind, targets, strict=True):
        assert float(r.component(kind).adjustment.amount) == pytest.approx(
            target, rel=0.0, abs=1e-12
        )
        assert math.fsum(r.component(kind).contributions) == float(
            r.component(kind).adjustment.amount
        )
    assert float(r.total_adjustment.amount) == pytest.approx(math.fsum(targets), rel=0.0, abs=1e-12)
    assert float(r.funding_cost.amount) == 2.0
    assert float(r.funding_benefit.amount) == 0.5
    assert r.model_version == "0.7.0" and len(r.hash) == 64
    assert dict(r.attribution)["discount"] == curve().curve_hash


@pytest.mark.parametrize(
    "hazard,recovery,positive", [(0.0, 0.4, 100.0), (0.2, 1.0, 100.0), (0.2, 0.4, 0.0)]
)
def test_zero_default_full_recovery_and_zero_exposure_limits(hazard, recovery, positive):
    r = result(
        counterparty=PiecewiseHazardCurve((0.0, 2.0), (hazard,)),
        recovery=RecoveryAssumption(recovery),
        profile=exposure(positive=(positive,) * 3),
    )
    assert r.component(ComponentKind.CVA).adjustment.amount == 0


def test_dva_is_positive_payable_magnitude_and_own_limits():
    r = result(own=replace(own(), recovery=RecoveryAssumption(1)))
    assert r.component(ComponentKind.DVA).adjustment.amount == 0
    r = result(own=replace(own(), hazard=PiecewiseHazardCurve((0.0, 2.0), (0.0,))))
    assert r.component(ComponentKind.DVA).adjustment.amount == 0
    assert (
        result(profile=exposure(negative=(0.0,) * 3)).component(ComponentKind.DVA).adjustment.amount
        == 0
    )


def test_funding_benefit_is_explicit_and_margin_not_reusable_ia():
    r = result(funding=funding(benefit=False), margin=margin(posted_initial_margin=(0.0,) * 3))
    assert r.funding_benefit.amount == 0
    assert r.component(ComponentKind.FVA).adjustment.amount == -2
    assert r.component(ComponentKind.MVA).adjustment.amount == 0
    r = result(margin=margin(posted_initial_margin=(0.0, 10.0, 20.0)))
    assert float(r.component(ComponentKind.MVA).adjustment.amount) == pytest.approx(
        -0.4, rel=0.0, abs=1e-15
    )
    assert result(margin=margin(posted_initial_margin=(100.0,) * 3)).funding_cost == r.funding_cost


def test_piecewise_funding_credit_knots_and_finite_horizon():
    spreads = FundingSpreadCurve((0.0, 0.5, 1.5, 3.0), (0.01, 0.02, 0.03))
    assert (
        spreads.spread(0.49) == 0.01 and spreads.spread(0.5) == 0.02 and spreads.spread(3) == 0.03
    )
    costs = funding_integral((0.0, 2.0), (100.0, 100.0), curve(), spreads)
    assert math.fsum(costs) == pytest.approx(
        100 * (0.5 * 0.01 + 1 * 0.02 + 0.5 * 0.03), rel=0.0, abs=1e-14
    )
    hazard = PiecewiseHazardCurve((0.0, 0.3, 1.7, 3.0), (0.1, 0.2, 0.3))
    losses = credit_integral((0.0, 2.0), (100.0, 100.0), curve(), hazard, RecoveryAssumption(0.4))
    assert math.fsum(losses) == pytest.approx(
        60 * hazard.default_probability(2), rel=0.0, abs=1e-13
    )
    with pytest.raises(DomainValidationError):
        spreads.spread(3.01)


def test_discount_default_quadrature_converges_to_known_integral():
    # Integral of 100*(1-R)*lambda*exp(-(r+lambda)*t), independent constant exposure.
    hazard = PiecewiseHazardCurve((0.0, 2.0), (0.2,))
    expected = 60 * 0.2 / 0.23 * (-math.expm1(-0.23 * 2))
    errors = []
    for steps in (16, 32, 64, 128):
        times = tuple(float(v) for v in np.linspace(0, 2, steps + 1))
        actual = math.fsum(
            credit_integral(
                times,
                (100.0,) * len(times),
                curve((0.0, 2.0), 0.03),
                hazard,
                RecoveryAssumption(0.4),
            )
        )
        errors.append(abs(actual - expected))
    assert errors[-1] < 2e-5
    assert all(a / b > 3.9 for a, b in zip(errors, errors[1:], strict=False))


def test_sampled_default_loss_no_second_pd_weight_and_no_default():
    amounts = np.array([[10, 20, 30], [0, 0, 0], [10, 20, 30]], dtype=np.float64)
    defaults = exposure_at_default(amounts, (0.0, 1.0, 2.0), (0.2, None, 1.3))
    costs = sampled_credit_loss((0.0, 1.0, 2.0), defaults, curve(), RecoveryAssumption(0.4))
    assert costs == pytest.approx((4.0, 6.0), rel=0.0, abs=1e-14)
    r = result(sampled_defaults=defaults)
    assert float(r.component(ComponentKind.CVA).adjustment.amount) == pytest.approx(
        -10, rel=0.0, abs=1e-14
    )
    assert "sampled_default" in r.component(ComponentKind.CVA).methodology
    empty = exposure_at_default(amounts, (0.0, 1.0, 2.0), (None, None, None))
    assert sampled_credit_loss((0.0, 1.0, 2.0), empty, curve(), RecoveryAssumption(0)) == (0.0, 0.0)


@given(
    st.floats(min_value=1, max_value=10000, allow_nan=False),
    st.floats(min_value=0, max_value=0.9, allow_nan=False),
)
@settings(max_examples=60, deadline=None)
def test_constant_positive_exposure_hazard_and_recovery_signs(amount, recovery):
    cp = PiecewiseHazardCurve((0.0, 2.0), (0.2,))
    a = math.fsum(
        credit_integral((0.0, 1.0, 2.0), (amount,) * 3, curve(), cp, RecoveryAssumption(recovery))
    )
    more_hazard = math.fsum(
        credit_integral(
            (0.0, 1.0, 2.0),
            (amount,) * 3,
            curve(),
            PiecewiseHazardCurve((0.0, 2.0), (0.3,)),
            RecoveryAssumption(recovery),
        )
    )
    more_recovery = math.fsum(
        credit_integral(
            (0.0, 1.0, 2.0), (amount,) * 3, curve(), cp, RecoveryAssumption(recovery + 0.05)
        )
    )
    assert more_hazard >= a and more_recovery <= a


@pytest.mark.parametrize(
    "changes",
    [
        {"discount": None},
        {"own": None},
        {"funding": None},
        {"margin": None},
        {"profile": None},
        {"counterparty": None},
        {"recovery": None},
        {"discount": curve(currency=Currency.EUR)},
        {"discount": curve((0.0, 1.0))},
        {"margin": margin(currency=Currency.EUR)},
        {"margin": margin((0.0, 2.0))},
        {"counterparty": PiecewiseHazardCurve((0.0, 1.0), (0.2,))},
        {"own": own(1.0)},
        {"funding": funding(1.0)},
        {"profile": exposure(expected_exposure=(1.0,))},
        {"profile": exposure(expected_negative_exposure=(-1.0, 1.0, 1.0))},
    ],
)
def test_invalid_xva_boundary(changes):
    with pytest.raises((DomainValidationError, NumericalError)):
        result(**changes)
