"""Independent targets, controlled misses, constrained optimization and arithmetic residuals."""

import math
from dataclasses import dataclass, replace

import pytest

from parallax_risk.application.adversarial_examples import (
    example,
    mutations,
    probe_case,
    probe_targets,
)
from parallax_risk.application.validation_forensics import Counterfactual, DiagnosticState, diagnose
from parallax_risk.application.validation_mutation import campaign
from parallax_risk.application.validation_probes import OperationProbeModel, probe_suite
from parallax_risk.application.validation_search import feasible, search
from parallax_risk.common.canonical import content_hash
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.contracts import Metric, ModelOutput, Tolerance
from parallax_risk.domain.validation.forensics import CauseKind, DiagnosticContext
from parallax_risk.domain.validation.mutation import MutationKind
from parallax_risk.domain.validation.search import LinearRestriction, SearchDimension, SearchSpec
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution


@dataclass(frozen=True)
class ScalarCase:
    value: float

    @property
    def hash(self):
        return content_hash(self.value)


class ScalarModel:
    def evaluate(self, case):
        return ModelOutput(
            case.hash,
            "scalar",
            "1",
            (Metric("value", case.value, "USD"),),
            content_hash(case.value),
            ("Synthetic scalar target",),
        )


class ZeroModel(ScalarModel):
    def evaluate(self, case):
        return replace(super().evaluate(case), metrics=(Metric("value", 0.0, "USD"),))


def spec(**changes):
    return replace(
        SearchSpec(
            (SearchDimension("x", "USD", 0.0, 2.0, "Synthetic scalar interval"),),
            (),
            StreamKey(872, 33, 1),
            "value",
            "Synthetic bounded research",
            50,
            5,
            255,
            1e-10,
            1e-10,
        ),
        **changes,
    )


def context(label="same"):
    return DiagnosticContext(*(content_hash((label, i)) for i in range(6)))


@pytest.mark.parametrize("kind", tuple(MutationKind))
def test_each_fault_changes_only_its_own_operation_and_is_detected(kind):
    case = probe_case()
    model = OperationProbeModel()
    mutation = next(m for m in mutations() if m.kind == kind)
    report = campaign(
        model,
        case,
        (mutation,),
        lambda o: probe_suite(o, probe_targets(case), Tolerance(1e-10, 1e-12)),
        "Synthetic hand formula reproduction",
    )
    item = report.evidence[0]
    assert all(c.passed for c in report.baseline_checks)
    assert item.detected and item.newly_failed == (f"probe-{kind}",)
    for a, b in zip(report.baseline.metrics, item.output.metrics, strict=True):
        assert (a.value != b.value) == (a.name == str(kind))
    assert case == probe_case()
    assert report.rates[0].rate == 1.0


def test_hand_probe_values_and_sampling_error():
    output = OperationProbeModel().evaluate(probe_case(), None)
    assert output.metric(str(MutationKind.FX)).value == 120.0
    assert output.metric(str(MutationKind.COLLATERAL)).value == 160.0
    assert output.metric(str(MutationKind.THRESHOLD)).value == 170.0
    assert output.metric(str(MutationKind.DATE)).value == 180.0
    assert output.metric(str(MutationKind.INTERPOLATION)).value == pytest.approx(0.9, abs=1e-15)
    # [1,2,4,8] mean 3.75, sample variance 115/12; SEM sqrt(115/48).
    assert output.metric(str(MutationKind.PATHS)).value == pytest.approx(
        math.sqrt(115 / 48), abs=1e-14
    )
    assert output.metric(str(MutationKind.LOOK_AHEAD)).value == 0.2
    assert output.metric(str(MutationKind.MPOR)).value == pytest.approx(0.3, abs=1e-15)


def test_demo_retains_true_misses_rates_nonconvergence_and_unexplained_residual():
    result = example(ScipyDifferentialEvolution())
    assert result.full_suite.rates[0].detected == 15
    assert result.weak_suite.rates[0].detected == 1
    assert result.weak_suite.rates[0].rate == pytest.approx(1 / 15, abs=1e-15)
    assert sum(not e.detected for e in result.weak_suite.evidence) == 14
    assert result.search.optimizer.iterations <= 2
    assert not result.search.optimizer.converged
    assert all(
        feasible(e.parameters, result.search.specification) for e in result.search.evaluations
    )
    assert result.diagnostics.materiality.passed is False
    assert result.diagnostics.residual < 0
    assert result.diagnostics.change == pytest.approx(
        math.fsum(s.change for s in result.diagnostics.steps) + result.diagnostics.residual,
        abs=1e-13,
    )
    assert all(c.passed for c in result.diagnostics.repeat_checks)
    assert len(result.diagnostics.causes) == 7


@pytest.mark.parametrize(
    "kind,changes",
    [
        (MutationKind.DISCOUNT, {"cva": replace(probe_case().cva, rate=0.0)}),
        (MutationKind.CORRELATION, {"correlation": 0.0}),
        (MutationKind.COLLATERAL, {"collateral": 0.0}),
        (MutationKind.THRESHOLD, {"threshold": 0.0}),
        (MutationKind.VOLATILITY, {"volatility": 0.0}),
        (MutationKind.RECOVERY, {"cva": replace(probe_case().cva, recovery=0.5)}),
        (MutationKind.FX, {"fx": 1.0}),
        (MutationKind.LOOK_AHEAD, {"as_of": probe_case().calibration_dates[-1]}),
    ],
)
def test_equivalent_mutations_are_honestly_missed(kind, changes):
    case = replace(probe_case(), **changes)
    mutation = next(m for m in mutations() if m.kind == kind)
    result = campaign(
        OperationProbeModel(),
        case,
        (mutation,),
        lambda o: probe_suite(o, probe_targets(case), Tolerance(1e-10)),
        "Retained equivalent fault",
    )
    assert result.evidence[0].detected is False
    assert result.rates[0].rate == 0.0


def test_baseline_failure_does_not_count_as_detection():
    case = probe_case()
    target = replace(probe_targets(case)[1], value=-10000.0)
    result = campaign(
        OperationProbeModel(),
        case,
        (mutations()[1],),
        lambda o: probe_suite(o, (target,), Tolerance(0.0)),
        "Bad target baseline",
    )
    assert not result.baseline_checks[0].passed
    assert not result.evidence[0].checks[0].passed
    assert not result.evidence[0].detected


def test_scipy_finds_independently_known_bounded_maximum_and_replays():
    class QuadraticModel(ScalarModel):
        def evaluate(self, case):
            return replace(
                super().evaluate(case),
                metrics=(Metric("value", 4 - (case.value - 1.25) ** 2, "USD"),),
            )

    args = (
        QuadraticModel(),
        ZeroModel(),
        lambda p: ScalarCase(p[0]),
        ScipyDifferentialEvolution(),
        spec(),
    )
    first = search(*args)
    assert first.best.parameters[0] == pytest.approx(1.25, abs=1e-5)
    assert first.best.discrepancy == pytest.approx(4.0, abs=1e-10)
    assert first.optimizer.converged
    assert first == search(*args)
    assert first.optimizer.evaluations <= 255


def test_feasible_constraint_changes_known_optimum():
    constraint = LinearRestriction("cap", (1.0,), 0.0, 0.6, "Synthetic scalar maximum")
    result = search(
        ScalarModel(),
        ZeroModel(),
        lambda p: ScalarCase(p[0]),
        ScipyDifferentialEvolution(),
        spec(
            restrictions=(constraint,),
            population_multiplier=20,
            maximum_iterations=60,
            maximum_evaluations=1220,
        ),
    )
    assert 0.599 <= result.best.parameters[0] <= 0.6
    assert all(e.parameters[0] <= 0.6 for e in result.evaluations)


def test_forensic_bridge_materiality_zero_residual_and_changed_contexts():
    before = DiagnosticState(ScalarCase(10.0), context("before"))
    after = DiagnosticState(ScalarCase(25.0), context("after"))
    report = diagnose(
        ScalarModel(),
        before,
        after,
        (
            Counterfactual(
                "middle", CauseKind.MARKET, DiagnosticState(ScalarCase(20.0), context())
            ),
            Counterfactual("endpoint", CauseKind.PORTFOLIO, after),
        ),
        "value",
        Tolerance(1.0),
        Tolerance(0.0),
        "Retained scalar bridge",
    )
    assert report.change == 15.0
    assert tuple(s.change for s in report.steps) == (10.0, 5.0)
    assert report.residual == 0.0
    assert sum(c.changed for c in report.causes) == 6
    assert all(c.passed for c in report.repeat_checks)
    unchanged = diagnose(
        ScalarModel(),
        before,
        before,
        (),
        "value",
        Tolerance(0.0),
        Tolerance(0.0),
        "Unchanged endpoints",
    )
    assert unchanged.materiality.passed and unchanged.change == 0.0


def test_actual_repeat_instability_is_recorded_with_unchanged_configuration():
    class Unstable(ScalarModel):
        def __init__(self):
            self.calls = 0

        def evaluate(self, case):
            self.calls += 1
            return replace(
                super().evaluate(case), metrics=(Metric("value", case.value + self.calls, "USD"),)
            )

    state = DiagnosticState(ScalarCase(10.0), context())
    report = diagnose(
        Unstable(),
        state,
        state,
        (),
        "value",
        Tolerance(1.0),
        Tolerance(0.0),
        "Actual synthetic unstable reruns",
    )
    assert not any(c.passed for c in report.repeat_checks)
    assert next(c for c in report.causes if c.kind == CauseKind.NUMERICS).changed


def test_actual_versioned_adapter_change_is_observed_without_causal_claim():
    class Versioned(ScalarModel):
        def evaluate(self, case):
            output = super().evaluate(case)
            # Two actual synthetic implementations chosen by an explicit case coordinate.
            if case.value > 1:
                return replace(
                    output, model_version="2", metrics=(Metric("value", case.value**2, "USD"),)
                )
            return output

    first = DiagnosticState(ScalarCase(1.0), context())
    second = DiagnosticState(ScalarCase(2.0), context())
    report = diagnose(
        Versioned(),
        first,
        second,
        (),
        "value",
        Tolerance(0.0),
        Tolerance(0.0),
        "Explicit synthetic model implementations",
    )
    assert report.change == 3.0
    assert next(c for c in report.causes if c.kind == CauseKind.VERSION).changed
    assert all(c.passed for c in report.repeat_checks)
