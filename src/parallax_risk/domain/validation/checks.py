"""Local finite differences, justified invariants and finite-study convergence criteria."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from scipy.stats import t

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.pricing._numbers import product, total
from parallax_risk.domain.simulation.statistics import Estimate
from parallax_risk.domain.validation.contracts import Check, Metric, Tolerance, check
from parallax_risk.domain.xva.contracts import fingerprint


def equality(
    name: str,
    actual: Metric,
    expected: float,
    tolerance: Tolerance,
    *,
    evidence: tuple[str, ...],
    reproduction: str,
    version: str,
) -> Check:
    expected = require_finite(expected, name="expected metric")
    if not isinstance(tolerance, Tolerance) or not isinstance(actual, Metric):
        raise DomainValidationError("Equality requires metric and tolerance")
    return check(
        name,
        actual,
        abs(total((actual.value, -expected))),
        tolerance.bound(expected),
        evidence=evidence,
        reproduction=reproduction,
        version=version,
    )


def monotonicity(
    name: str,
    values: tuple[Metric, ...],
    *,
    increasing: bool,
    tolerance: Tolerance,
    evidence: tuple[str, ...],
    reproduction: str,
    version: str,
) -> Check:
    """Check a caller-justified direction; exposure itself is not assumed time-monotone."""
    require_tuple(values, Metric, nonempty=True)
    if len(values) < 2 or type(increasing) is not bool or not isinstance(tolerance, Tolerance):
        raise DomainValidationError("Monotonicity requires multiple values and explicit direction")
    if any(v.schema != values[0].schema for v in values):
        raise DomainValidationError("Monotonic metrics must have the same schema")
    sign = 1.0 if increasing else -1.0
    excess = max(
        max(0.0, product(sign, total((a.value, -b.value))) - tolerance.bound(b.value))
        for a, b in zip(values, values[1:], strict=False)
    )
    return check(
        name, values[0], excess, 0.0, evidence=evidence, reproduction=reproduction, version=version
    )


@dataclass(frozen=True, slots=True)
class SensitivityValidation:
    bump: float
    observations: tuple[Metric, ...]
    derivative: float
    half_bump_derivative: float
    derivative_unit: str
    consistency: Check
    reference: Check | None


def sensitivity(
    revalue: Callable[[float], Metric],
    bump: float,
    factor_unit: str,
    tolerance: Tolerance,
    *,
    evidence: tuple[str, ...],
    reproduction: str,
    version: str,
    expected_derivative: float | None = None,
) -> SensitivityValidation:
    """Five actual local valuations, central h and h/2, optionally an independent target."""
    from parallax_risk.domain._validation import require_text

    bump = require_finite(bump, name="bump")
    require_text(factor_unit)
    if bump <= 0 or bump * 0.5 == 0 or not isinstance(tolerance, Tolerance):
        raise DomainValidationError("Sensitivity needs a resolved positive bump and tolerance")
    observations = tuple(revalue(x) for x in (0.0, bump, -bump, bump * 0.5, -bump * 0.5))
    require_tuple(observations, Metric)
    if any(v.schema != observations[0].schema for v in observations):
        raise DomainValidationError("Sensitivity valuations must retain their exact metric schema")
    derivative = require_finite(
        total((observations[1].value, -observations[2].value)) / product(2.0, bump),
        name="derivative",
    )
    half = require_finite(
        total((observations[3].value, -observations[4].value)) / bump, name="half derivative"
    )
    unit = f"{observations[0].unit} per {factor_unit}"
    metric = Metric(observations[0].name, derivative, unit)
    consistency = equality(
        "finite-difference-consistency",
        metric,
        half,
        tolerance,
        evidence=evidence,
        reproduction=reproduction,
        version=version,
    )
    reference = (
        None
        if expected_derivative is None
        else equality(
            "sensitivity-reference",
            metric,
            expected_derivative,
            tolerance,
            evidence=evidence,
            reproduction=reproduction,
            version=version,
        )
    )
    return SensitivityValidation(bump, observations, derivative, half, unit, consistency, reference)


class ConvergenceAxis(StrEnum):
    PATH_COUNT = "path_count"
    TIME_STEP = "maximum_time_step_years"


@dataclass(frozen=True, slots=True)
class ConvergencePoint:
    resolution: float
    estimate: Estimate
    input_hash: str

    def __post_init__(self) -> None:
        if require_finite(self.resolution, name="resolution") <= 0 or not isinstance(
            self.estimate, Estimate
        ):
            raise DomainValidationError(
                "Convergence point requires positive resolution and estimate"
            )
        fingerprint(self.input_hash)
        e = self.estimate
        for value in (
            e.mean,
            e.sample_variance,
            e.standard_error,
            e.confidence,
            *e.confidence_interval,
        ):
            require_finite(value, name="estimate")
        if (
            type(e.independent_units) is not int
            or e.independent_units < 2
            or type(e.total_paths) is not int
            or e.total_paths < e.independent_units
            or e.sample_variance < 0
            or e.standard_error < 0
            or not 0 < e.confidence < 1
            or not e.confidence_interval[0] <= e.mean <= e.confidence_interval[1]
        ):
            raise DomainValidationError("Invalid independent-unit estimate")
        if (
            e.sampling_unit not in ("iid_path", "antithetic_pair", "independent_scramble")
            or (e.sampling_unit == "iid_path" and e.total_paths != e.independent_units)
            or (e.sampling_unit == "antithetic_pair" and e.total_paths != 2 * e.independent_units)
            or not math.isclose(
                e.standard_error,
                math.sqrt(e.sample_variance / e.independent_units),
                rel_tol=1e-12,
                abs_tol=0.0,
            )
            or e.interval_method != "Student_t_approximation_for_independent_units"
        ):
            raise DomainValidationError(
                "Convergence estimate sampling convention or standard error inconsistent"
            )
        width = require_finite(
            float(t.isf((1 - e.confidence) / 2, e.independent_units - 1)) * e.standard_error,
            name="independent estimate width",
        )
        if any(
            not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-14)
            for actual, expected in zip(
                e.confidence_interval, (e.mean - width, e.mean + width), strict=True
            )
        ):
            raise DomainValidationError(
                "Convergence confidence bounds do not match the declared t method"
            )


@dataclass(frozen=True, slots=True)
class ConvergenceStudy:
    axis: ConvergenceAxis
    metric: str
    unit: str
    points: tuple[ConvergencePoint, ...]
    adjacent_checks: tuple[Check, ...]
    precision_check: Check
    passed: bool
    interpretation: str = (
        "finite ladder stability and final sampling precision; not a bound on discretization bias"
    )


def convergence(
    axis: ConvergenceAxis,
    metric: str,
    unit: str,
    points: tuple[ConvergencePoint, ...],
    stability: Tolerance,
    precision: Tolerance,
    *,
    reproduction: str,
    version: str,
) -> ConvergenceStudy:
    require_tuple(points, ConvergencePoint, nonempty=True)
    if (
        not isinstance(axis, ConvergenceAxis)
        or len(points) < 2
        or not isinstance(stability, Tolerance)
        or not isinstance(precision, Tolerance)
    ):
        raise DomainValidationError(
            "Convergence requires typed axis, tolerances and at least two levels"
        )
    direction = 1 if axis == ConvergenceAxis.PATH_COUNT else -1
    if any(
        direction * (b.resolution - a.resolution) <= 0
        for a, b in zip(points, points[1:], strict=False)
    ):
        raise DomainValidationError("Path counts must increase; time steps must decrease")
    if axis == ConvergenceAxis.PATH_COUNT and any(
        p.resolution != p.estimate.total_paths for p in points
    ):
        raise DomainValidationError("Path resolution must equal actual path count")
    if len({(p.estimate.confidence, p.estimate.sampling_unit) for p in points}) != 1:
        raise DomainValidationError(
            "Convergence estimates must share confidence and sampling convention"
        )
    checks = tuple(
        equality(
            f"convergence-level-{i}",
            Metric(metric, b.estimate.mean, unit),
            a.estimate.mean,
            stability,
            evidence=(
                a.input_hash,
                b.input_hash,
                "Adjacent mean difference; no paired-difference CI inferred",
            ),
            reproduction=reproduction,
            version=version,
        )
        for i, (a, b) in enumerate(zip(points, points[1:], strict=False), start=1)
    )
    final = points[-1]
    width = max(
        total((final.estimate.mean, -final.estimate.confidence_interval[0])),
        total((final.estimate.confidence_interval[1], -final.estimate.mean)),
    )
    result = check(
        "convergence-final-precision",
        Metric(metric, final.estimate.mean, unit),
        width,
        precision.bound(final.estimate.mean),
        evidence=(final.input_hash, final.estimate.interval_method),
        reproduction=reproduction,
        version=version,
    )
    return ConvergenceStudy(
        axis, metric, unit, points, checks, result, all(c.passed for c in checks) and result.passed
    )
