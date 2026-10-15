"""Malformed provenance, budgets, schema changes and inadmissible numerical inputs fail."""

from dataclasses import replace
from datetime import date

import pytest

from parallax_risk.application.adversarial_examples import mutations, probe_case, probe_targets
from parallax_risk.application.validation_forensics import Counterfactual, DiagnosticState, diagnose
from parallax_risk.application.validation_mutation import campaign
from parallax_risk.application.validation_probes import OperationProbeModel, probe_suite
from parallax_risk.application.validation_search import feasible, search
from parallax_risk.common.errors import ParallaxError
from parallax_risk.domain.validation.contracts import Metric, Tolerance
from parallax_risk.domain.validation.forensics import CauseKind, DiagnosticContext
from parallax_risk.domain.validation.search import (
    LinearRestriction,
    OptimizerResult,
)
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution
from tests.quantitative.test_adversarial_lab import (
    ScalarCase,
    ScalarModel,
    ZeroModel,
    context,
    spec,
)


@pytest.mark.parametrize(
    "changes",
    [
        {"cva": None},
        {"start": date(2026, 1, 1)},
        {"fx": 0.0},
        {"fx": True},
        {"fx": float("inf")},
        {"correlation": 1.0},
        {"correlation": float("nan")},
        {"collateral": -1.0},
        {"threshold": -1.0},
        {"volatility": -1.0},
        {"mpor_business_days": 9},
        {"mpor_business_days": True},
        {"samples": (1.0, 2.0)},
        {"samples": [1.0, 2.0, 3.0, 4.0]},
        {"samples": (1.0, 2.0, float("nan"), 4.0)},
        {"calibrated_hazards": (0.2,)},
        {"calibrated_hazards": (-0.1, 0.2)},
        {"calibration_dates": (date(2025, 1, 1), date(2025, 1, 1))},
        {"as_of": date(2024, 1, 1)},
    ],
)
def test_probe_rejects_invalid_economic_and_time_domains(changes):
    with pytest.raises(ParallaxError):
        replace(probe_case(), **changes)


@pytest.mark.parametrize(
    "changes",
    [{"name": ""}, {"kind": "discount_factor_error"}, {"category": ""}, {"description": ""}],
)
def test_mutation_requires_explicit_typed_provenance(changes):
    with pytest.raises(ParallaxError):
        replace(mutations()[0], **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"lower": 2.0},
        {"upper": 0.0},
        {"upper": float("inf")},
        {"lower": True},
        {"unit": ""},
        {"rationale": ""},
        {"name": ""},
    ],
)
def test_dimension_invalid(changes):
    with pytest.raises(ParallaxError):
        replace(spec().dimensions[0], **changes)


@pytest.mark.parametrize(
    "args",
    [
        ("c", (0.0,), 0.0, 1.0, "why"),
        ("c", (1.0,), 2.0, 1.0, "why"),
        ("c", (float("nan"),), 0.0, 1.0, "why"),
        ("c", [1.0], 0.0, 1.0, "why"),
    ],
)
def test_constraint_invalid(args):
    with pytest.raises(ParallaxError):
        LinearRestriction(*args)


@pytest.mark.parametrize(
    "changes",
    [
        {"dimensions": ()},
        {"dimensions": (spec().dimensions[0],) * 2},
        {"key": None},
        {"restrictions": (LinearRestriction("c", (1.0, 1.0), 0.0, 1.0, "why"),)},
        {"restrictions": (LinearRestriction("c", (1.0,), 0.0, 1.0, "why"),) * 2},
        {"maximum_iterations": -1},
        {"population_multiplier": 0},
        {"maximum_evaluations": 1},
        {"convergence_relative": -1.0},
        {"convergence_absolute": float("nan")},
    ],
)
def test_search_spec_invalid(changes):
    with pytest.raises(ParallaxError):
        spec(**changes)


@pytest.mark.parametrize("parameters", [(0.0, 1.0), [0.0], (float("nan"),), (True,)])
def test_feasibility_invalid(parameters):
    with pytest.raises(ParallaxError):
        feasible(parameters, spec())


def test_probe_validation_bad_targets_and_adapter_inputs():
    model = OperationProbeModel()
    case = probe_case()
    output = model.evaluate(case, None)
    for first, second in ((None, None), (case, "invalid")):
        with pytest.raises(ParallaxError):
            model.evaluate(first, second)
    target = probe_targets(case)[0]
    for targets in ((target, target), (replace(target, unit="wrong"),)):
        with pytest.raises(ParallaxError):
            probe_suite(output, targets, Tolerance(0.0))


@pytest.mark.parametrize(
    "mutants,budget",
    [
        ((), 100),
        ((mutations()[0],) * 2, 100),
        ((mutations()[0],), 1),
        ((replace(mutations()[0], category="ALL"),), 100),
    ],
)
def test_campaign_prevalidates_budget_names_and_reservation(mutants, budget):
    class Forbidden:
        def evaluate(self, *args):
            raise AssertionError("No evaluation authorized")

    with pytest.raises(ParallaxError):
        campaign(
            Forbidden(),
            probe_case(),
            mutants,
            lambda o: (),
            "Reproduce",
            maximum_evaluations=budget,
        )


@pytest.mark.parametrize(
    "mode",
    [
        "untyped",
        "stale",
        "duplicate",
        "invalid-bool",
        "changed-checks",
        "changed-metrics",
        "throws",
    ],
)
def test_campaign_rejects_invalid_model_suite_and_propagates_errors(mode):
    class Changed:
        def evaluate(self, case, mutation):
            if mode == "throws":
                raise RuntimeError("Actual valuation failed")
            out = OperationProbeModel().evaluate(case, mutation)
            if mode == "untyped":
                return None
            if mode == "stale":
                return replace(out, case_hash="b" * 64)
            if mode == "changed-metrics" and mutation is not None:
                return replace(out, metrics=out.metrics[:-1])
            return out

    calls = 0

    def suite(output):
        nonlocal calls
        calls += 1
        checks = probe_suite(output, (probe_targets(probe_case())[0],), Tolerance(0.0))
        if mode == "duplicate":
            return checks * 2
        if mode == "invalid-bool":
            return (replace(checks[0], passed=1),)
        if mode == "changed-checks" and calls == 2:
            return (replace(checks[0], name="another"),)
        return checks

    with pytest.raises(RuntimeError if mode == "throws" else ParallaxError):
        campaign(Changed(), probe_case(), (mutations()[0],), suite, "Reproduce")


class OneEvaluation:
    def __init__(self, change=None, coordinates=(0.5,)):
        self.change = change
        self.coordinates = coordinates

    def maximize(self, objective, specification):
        value = objective(self.coordinates)
        result = OptimizerResult(
            self.coordinates, value, False, "Budget completed", 0, 1, "Injected test optimizer"
        )
        return self.change(result) if self.change else result


@pytest.mark.parametrize(
    "change",
    [
        lambda r: None,
        lambda r: replace(r, parameters=(3.0,)),
        lambda r: replace(r, parameters=(0.4,)),
        lambda r: replace(r, objective=r.objective + 1),
        lambda r: replace(r, evaluations=2),
        lambda r: replace(r, converged=1),
        lambda r: replace(r, iterations=-1),
        lambda r: replace(r, iterations=100),
        lambda r: replace(r, message=""),
        lambda r: replace(r, implementation=""),
    ],
)
def test_optimizer_cannot_fabricate_or_change_retained_results(change):
    with pytest.raises(ParallaxError):
        search(
            ScalarModel(), ZeroModel(), lambda p: ScalarCase(p[0]), OneEvaluation(change), spec()
        )


def test_no_feasible_population_and_foreign_parameters_rejected():
    with pytest.raises(ParallaxError):
        search(
            ScalarModel(),
            ZeroModel(),
            lambda p: ScalarCase(p[0]),
            OneEvaluation(coordinates=(3.0,)),
            spec(),
        )
    impossible = spec(
        restrictions=(
            LinearRestriction("impossible", (1.0,), 3.0, 4.0, "Synthetic empty feasible set"),
        ),
        maximum_iterations=0,
        maximum_evaluations=5,
    )
    with pytest.raises(ParallaxError, match="no feasible"):
        search(
            ScalarModel(),
            ZeroModel(),
            lambda p: ScalarCase(p[0]),
            ScipyDifferentialEvolution(),
            impossible,
        )


@pytest.mark.parametrize("mode", ["stale", "untyped", "wrong-unit", "identity", "schema"])
def test_search_rejects_stale_outputs_and_moving_model_schemas(mode):
    class Bad(ScalarModel):
        def __init__(self):
            self.calls = 0

        def evaluate(self, case):
            self.calls += 1
            output = super().evaluate(case)
            if mode == "untyped":
                return None
            if mode == "stale":
                return replace(output, case_hash="c" * 64)
            if mode == "wrong-unit":
                return replace(output, metrics=(Metric("value", 1.0, "EUR"),))
            if self.calls == 2:
                if mode == "identity":
                    return replace(output, model_version="2")
                return replace(output, metrics=(Metric("value", 1.0, "EUR"),))
            return output

    class Twice(OneEvaluation):
        def maximize(self, objective, specification):
            objective((0.5,))
            return super().maximize(objective, specification)

    with pytest.raises(ParallaxError):
        search(Bad(), ZeroModel(), lambda p: ScalarCase(p[0]), Twice(), spec())


def test_search_actual_budget_guard_not_only_planned_budget():
    class OverBudget:
        def maximize(self, objective, specification):
            for _ in range(6):
                objective((0.5,))
            raise AssertionError("Should reject sixth call")

    with pytest.raises(ParallaxError, match="exhausted"):
        search(
            ScalarModel(),
            ZeroModel(),
            lambda p: ScalarCase(p[0]),
            OverBudget(),
            spec(maximum_iterations=0, maximum_evaluations=5),
        )


@pytest.mark.parametrize(
    "mode", ["stale", "untyped", "endpoint-unit", "repeat-identity", "step-unit"]
)
def test_forensic_model_guard(mode):
    class Bad(ScalarModel):
        def __init__(self):
            self.calls = 0

        def evaluate(self, case):
            self.calls += 1
            out = super().evaluate(case)
            if mode == "stale":
                return replace(out, case_hash="f" * 64)
            if mode == "untyped":
                return None
            if (mode == "endpoint-unit" and self.calls == 2) or (
                mode == "step-unit" and self.calls == 5
            ):
                return replace(out, metrics=(Metric("value", 1.0, "EUR"),))
            if mode == "repeat-identity" and self.calls == 3:
                return replace(out, model_version="2")
            return out

    state = DiagnosticState(ScalarCase(1.0), context())
    with pytest.raises(ParallaxError):
        diagnose(
            Bad(),
            state,
            state,
            (Counterfactual("step", CauseKind.MARKET, state),),
            "value",
            Tolerance(0.0),
            Tolerance(0.0),
            "Reproduce",
        )


def test_context_state_step_and_diagnostic_budget_guards():
    with pytest.raises(ParallaxError):
        DiagnosticContext("invalid", *("a" * 64 for _ in range(5)))
    with pytest.raises(ParallaxError):
        DiagnosticState(ScalarCase(1.0), None)
    state = DiagnosticState(ScalarCase(1.0), context())
    with pytest.raises(ParallaxError):
        Counterfactual("step", "market_movement", state)
    with pytest.raises(ParallaxError):
        Counterfactual("step", CauseKind.MARKET, None)
    steps = (Counterfactual("step", CauseKind.MARKET, state),) * 2
    with pytest.raises(ParallaxError):
        diagnose(
            ScalarModel(), state, state, steps, "value", Tolerance(0.0), Tolerance(0.0), "Reproduce"
        )
    with pytest.raises(ParallaxError):
        diagnose(
            ScalarModel(),
            state,
            state,
            (),
            "value",
            Tolerance(0.0),
            Tolerance(0.0),
            "Reproduce",
            maximum_evaluations=3,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"observed": -1.0},
        {"allowed": -1.0},
        {"observed": float("nan")},
        {"passed": False},
        {"finding": None, "observed": 1.0, "allowed": 0.0, "passed": False},
    ],
)
def test_campaign_rejects_fabricated_check_outcomes(changes):
    def suite(output):
        check = probe_suite(output, (probe_targets(probe_case())[0],), Tolerance(1.0))[0]
        return (replace(check, **changes),)

    with pytest.raises(ParallaxError):
        campaign(OperationProbeModel(), probe_case(), (mutations()[0],), suite, "Reproduce")


def test_scipy_preserves_economic_validation_failure_in_callback():
    def forbidden(parameters):
        raise ValueError("Economic input rejected explicitly")

    with pytest.raises(ValueError, match="Economic input rejected"):
        search(ScalarModel(), ZeroModel(), forbidden, ScipyDifferentialEvolution(), spec())
    with pytest.raises(ParallaxError):
        search(ScalarModel(), ZeroModel(), lambda p: ScalarCase(p[0]), OneEvaluation(), None)


def test_mutation_suite_cannot_change_acceptance_threshold_after_baseline():
    calls = 0

    def suite(output):
        nonlocal calls
        calls += 1
        result = probe_suite(output, (probe_targets(probe_case())[0],), Tolerance(1.0))[0]
        return (replace(result, allowed=2.0),) if calls > 1 else (result,)

    with pytest.raises(ParallaxError, match="schemas"):
        campaign(OperationProbeModel(), probe_case(), (mutations()[0],), suite, "Reproduce")
