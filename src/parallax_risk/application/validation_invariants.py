"""Automatically revalue justified independent-CVA invariants on actual production code."""

from dataclasses import replace

from parallax_risk.application.validation_models import ProductionCvaModel
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.pricing._numbers import product
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase
from parallax_risk.domain.validation.checks import equality, monotonicity
from parallax_risk.domain.validation.contracts import Check, Tolerance


def cva_invariants(
    model: ProductionCvaModel,
    case: CvaBenchmarkCase,
    tolerance: Tolerance,
    reproduction: str,
    *,
    scale: float = 2.0,
    collateral: float = 10.0,
) -> tuple[Check, ...]:
    """Constant reusable cash exposure offset, not dynamic CSA or time-monotone EE."""
    scale = require_finite(scale, name="trade scaling factor")
    collateral = require_finite(collateral, name="held cash collateral")
    if scale <= 0 or collateral < 0:
        raise DomainValidationError(
            "Invariant scaling must be positive and held collateral nonnegative"
        )
    base = model.evaluate(case)
    cases = (
        replace(case, hazard=0.0),
        replace(case, recovery=1.0),
        replace(case, exposure=(0.0,) * len(case.times)),
        replace(case, exposure=tuple(product(scale, value) for value in case.exposure)),
    )
    results = tuple(model.evaluate(c) for c in cases)
    checks = tuple(
        equality(
            name,
            r.metric("CVA"),
            expected,
            tolerance,
            evidence=(
                case.hash,
                c.hash,
                r.evidence_hash,
                "Independent deterministic-profile CVA; signed costs negative",
            ),
            reproduction=reproduction,
            version=r.model_version,
        )
        for name, expected, c, r in zip(
            ("zero-PD", "full-recovery", "zero-exposure", "linear-trade-scaling"),
            (0.0, 0.0, 0.0, product(scale, base.metric("CVA").value)),
            cases,
            results,
            strict=True,
        )
    )
    secured = replace(case, exposure=tuple(max(0.0, value - collateral) for value in case.exposure))
    secure_result = model.evaluate(secured)
    collateral_check = monotonicity(
        "held-collateral-reduces-loss",
        (base.metric("CVA"), secure_result.metric("CVA")),
        increasing=True,
        tolerance=tolerance,
        evidence=(base.hash, secure_result.hash, "Fixed reusable cash; CVA moves toward zero"),
        reproduction=reproduction,
        version=base.model_version,
    )
    return (*checks, collateral_check)
