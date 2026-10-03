"""Calibration domains, explicit identification limits and strict ingestion."""

from dataclasses import replace
from datetime import timedelta

import numpy as np
import pytest
from pydantic import ValidationError

from parallax_risk.application.calibration_inputs import CalibrationRequest
from parallax_risk.common.errors import CalibrationError, NumericalError, ParallaxError
from parallax_risk.common.identifiers import CalibrationRunId, QuoteId
from parallax_risk.domain.calibration.contracts import CalibrationSettings, ParameterBound
from parallax_risk.domain.calibration.problems import (
    BondOptionObservation,
    CallObservation,
    DiscountObservation,
)
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares, _uncertainty
from tests.fixtures.stochastic import (
    AS_OF,
    SOURCE,
    heston_problem,
    hull_white_problem,
    vasicek_problem,
)


@pytest.mark.parametrize(
    "args",
    [
        ("a", 0, 1, 2),
        ("a", 3, 1, 2),
        ("a", 1, 2, 2),
        ("a", 1, 2, 1),
        ("a", 1, float("nan"), 2),
        ("bad name", 1, 0, 2),
    ],
)
def test_invalid_bounds(args):
    with pytest.raises(ParallaxError):
        ParameterBound(*args)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_evaluations": 0},
        {"max_evaluations": True},
        {"function_tolerance": 0},
        {"parameter_tolerance": 1e-16},
        {"gradient_tolerance": 1},
        {"maximum_condition_number": 1},
    ],
)
def test_invalid_optimizer_settings(kwargs):
    with pytest.raises(ParallaxError):
        CalibrationSettings(**kwargs)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DiscountObservation(QuoteId("q"), 0, 1.0, SOURCE),
        lambda: DiscountObservation(QuoteId("q"), 1, 0.0, SOURCE),
        lambda: DiscountObservation("q", 1, 1.0, SOURCE),
        lambda: DiscountObservation(QuoteId("q"), 1, 1.0, object()),
        lambda: DiscountObservation(QuoteId("q"), 1, 1.0, SOURCE, 0),
        lambda: BondOptionObservation(QuoteId("q"), 1, 1, 1, 0.01, SOURCE),
        lambda: BondOptionObservation(QuoteId("q"), 0, 1, 1, 0.01, SOURCE),
        lambda: CallObservation(QuoteId("q"), 1, -1, 0.01, SOURCE),
        lambda: CallObservation(QuoteId("q"), 1, 100, -0.01, SOURCE),
    ],
)
def test_invalid_quotes(factory):
    with pytest.raises(ParallaxError):
        factory()


def test_dataset_provenance_and_instrument_uniqueness():
    problem, _, _ = vasicek_problem()
    for changes in (
        {"currency": "USD"},
        {"observations": ()},
        {"observations": (problem.observations[0],) * 2},
        {
            "observations": (
                problem.observations[0],
                replace(problem.observations[0], quote_id=QuoteId("other")),
            )
        },
        {"as_of": AS_OF - timedelta(seconds=1)},
        {"as_of": AS_OF.replace(tzinfo=None)},
    ):
        with pytest.raises(ParallaxError):
            replace(problem, **changes)
    hw, _, _ = hull_white_problem()
    with pytest.raises(CalibrationError):
        replace(hw, initial_curve=object())
    with pytest.raises(CalibrationError):
        replace(
            hw,
            observations=(
                hw.observations[0],
                replace(hw.observations[0], quote_id=QuoteId("other")),
            ),
        )
    with pytest.raises(CalibrationError):
        replace(hw, observations=(replace(hw.observations[0], value=2),))
    heston, _, _ = heston_problem()
    with pytest.raises(CalibrationError):
        replace(heston, fourier_settings=object())
    with pytest.raises(CalibrationError):
        replace(
            heston,
            observations=(
                heston.observations[0],
                replace(heston.observations[0], quote_id=QuoteId("other")),
            ),
        )
    with pytest.raises(CalibrationError):
        replace(heston, observations=(replace(heston.observations[0], value=200),))


def test_optimizer_rejects_mismatched_parameters_and_invalid_domain_bounds():
    problem, bounds, _ = vasicek_problem()
    solver = ScipyLeastSquares()
    with pytest.raises(CalibrationError):
        solver.solve(problem, bounds, object(), CalibrationRunId("bad"))
    with pytest.raises(CalibrationError):
        solver.solve(problem, bounds, CalibrationSettings(), "bad")
    with pytest.raises(ParallaxError):
        solver.solve(problem, (), CalibrationSettings(), CalibrationRunId("bad"))
    with pytest.raises(CalibrationError, match="order"):
        solver.solve(
            problem, tuple(reversed(bounds)), CalibrationSettings(), CalibrationRunId("bad")
        )
    with pytest.raises(CalibrationError, match="evaluation") as info:
        solver.solve(
            problem,
            (replace(bounds[0], lower=0), *bounds[1:]),
            CalibrationSettings(),
            CalibrationRunId("bad"),
        )
    assert isinstance(info.value.__cause__, ParallaxError)


def test_uncertainty_rejects_unsupported_statistical_claims():
    settings = CalibrationSettings()
    result = _uncertainty(np.eye(2), (0.0, 0.0), (0, 0), True, settings)
    assert result.unavailable_reason == "no_residual_degrees_of_freedom"
    result = _uncertainty(
        np.array([[1.0, 0.0], [0.0, 1e-12], [0.0, 0.0]]), (0.1, 0.1, 0.1), (0, 0), True, settings
    )
    assert result.unavailable_reason == "ill_conditioned_jacobian"
    with pytest.raises(CalibrationError, match="non-finite Jacobian"):
        _uncertainty(np.array([[float("nan")]]), (0.0,), (0,), True, settings)


def source_payload():
    return {
        "name": SOURCE.name,
        "reference": SOURCE.reference,
        "observed_at": AS_OF.isoformat(),
        "is_sample": True,
    }


def request_payload(kind):
    factory = {
        "vasicek": vasicek_problem,
        "hull_white": hull_white_problem,
        "heston": heston_problem,
    }[kind]
    problem, bounds, _ = factory()
    observations = []
    for p in problem.observations:
        item = {
            "quote_id": str(p.quote_id),
            "value": p.value,
            "source": source_payload(),
            "scale": p.scale,
        }
        for name in ("maturity", "expiry", "strike"):
            if hasattr(p, name):
                item[name] = getattr(p, name)
        observations.append(item)
    payload = {
        "kind": kind,
        "currency": "USD",
        "as_of": AS_OF.isoformat(),
        "observations": observations,
    }
    if kind == "vasicek":
        payload["initial_rate"] = problem.initial_rate
    elif kind == "hull_white":
        payload.update(
            forward_level=problem.initial_curve.level, forward_slope=problem.initial_curve.slope
        )
    else:
        payload.update(spot=problem.spot, rate=problem.rate, dividend=problem.dividend)
    return {
        "calibration_id": "boundary",
        "problem": payload,
        "bounds": [
            {"name": b.name, "initial": b.initial, "lower": b.lower, "upper": b.upper}
            for b in bounds
        ],
    }, problem


@pytest.mark.parametrize("kind", ["vasicek", "hull_white", "heston"])
def test_strict_boundary_round_trip(kind):
    payload, problem = request_payload(kind)
    mapped, bounds, settings, run_id = CalibrationRequest.model_validate(payload).to_domain()
    assert mapped == problem and mapped.input_hash == problem.input_hash
    assert run_id == CalibrationRunId("boundary") and settings == CalibrationSettings()
    assert tuple(b.name for b in bounds) == problem.parameter_names


@pytest.mark.parametrize("value", ["0.02", True, float("nan"), float("inf")])
def test_numeric_coercion_and_nonfinite_boundary_rejected(value):
    payload, _ = request_payload("vasicek")
    payload["problem"]["initial_rate"] = value
    with pytest.raises(ValidationError):
        CalibrationRequest.model_validate(payload)


@pytest.mark.parametrize("value", [0, "2025-01-01T00:00:00", None])
def test_asof_requires_explicit_timezone(value):
    payload, _ = request_payload("vasicek")
    payload["problem"]["as_of"] = value
    with pytest.raises((ValidationError, ParallaxError)):
        CalibrationRequest.model_validate(payload)


def test_unrecognized_model_extra_payload_and_model_evaluation_failures():
    payload, _ = request_payload("vasicek")
    payload["problem"]["kind"] = "other"
    with pytest.raises(ValidationError):
        CalibrationRequest.model_validate(payload)
    payload, _ = request_payload("vasicek")
    payload["surprise"] = True
    with pytest.raises(ValidationError):
        CalibrationRequest.model_validate(payload)

    class BrokenProblem:
        parameter_names = ("x",)
        observed = (1.0,)
        scales = (1.0,)

        def predict(self, x):
            raise NumericalError("explicit model failure")

    with pytest.raises(CalibrationError, match="evaluation"):
        ScipyLeastSquares().solve(
            BrokenProblem(),
            (ParameterBound("x", 1, 0, 2),),
            CalibrationSettings(),
            CalibrationRunId("broken"),
        )
    broken = BrokenProblem()
    broken.observed = ()
    with pytest.raises(CalibrationError, match="observations"):
        ScipyLeastSquares().solve(
            broken,
            (ParameterBound("x", 1, 0, 2),),
            CalibrationSettings(),
            CalibrationRunId("broken"),
        )
    broken.observed = (1.0,)
    broken.scales = (0.0,)
    with pytest.raises(CalibrationError, match="scales"):
        ScipyLeastSquares().solve(
            broken,
            (ParameterBound("x", 1, 0, 2),),
            CalibrationSettings(),
            CalibrationRunId("broken"),
        )
