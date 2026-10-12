"""Discounted unilateral credit and explicit additive funding/IM quadratures."""

from bisect import bisect_left, bisect_right

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import (
    ExposureAtDefault,
    ExposureProfile,
    validate_times,
)
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.pricing._numbers import priced_money, product, total
from parallax_risk.domain.xva.contracts import (
    ComponentKind,
    FundingSpreadCurve,
    FundingTerms,
    MarginProfile,
    OwnCredit,
    XvaComponent,
    XvaResult,
    magnitudes,
)


def _linear(times: tuple[float, ...], values: tuple[float, ...], time: float) -> float:
    """Declared linear profile interpolation inside its finite supplied horizon."""
    if time == times[-1]:
        return values[-1]
    i = bisect_right(times, time) - 1
    weight = (time - times[i]) / (times[i + 1] - times[i])
    return total((product(1 - weight, values[i]), product(weight, values[i + 1])))


def _grid(times: tuple[float, ...], *knots: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(sorted(set(times) | {t for nodes in knots for t in nodes if 0 <= t <= times[-1]}))


def credit_integral(
    times: tuple[float, ...],
    exposure: tuple[float, ...],
    discount: DiscountCurve,
    hazard: PiecewiseHazardCurve,
    recovery: RecoveryAssumption,
) -> tuple[float, ...]:
    """Positive loss magnitudes: endpoint-average D*EE times exact default increments.

    Refine on exposure/discount/hazard knots; no assumption of time-monotone exposure.
    Independent credit and deterministic discounting are explicit factorization assumptions.
    """
    _validate(times, exposure, discount)
    if not isinstance(hazard, PiecewiseHazardCurve) or not isinstance(recovery, RecoveryAssumption):
        raise DomainValidationError("Credit valuation requires explicit curve and recovery")
    if hazard.times[-1] < times[-1]:
        raise DomainValidationError("Default curve must cover exposure horizon")
    nodes = _grid(times, discount.times, hazard.times)
    values = tuple(product(discount.discount(t), _linear(times, exposure, t)) for t in nodes)
    return tuple(
        product(
            recovery.loss_given_default, total((va * 0.5, vb * 0.5)), hazard.default_increment(a, b)
        )
        for a, b, va, vb in zip(nodes, nodes[1:], values, values[1:], strict=False)
    )


def funding_integral(
    times: tuple[float, ...],
    amounts: tuple[float, ...],
    discount: DiscountCurve,
    spread: FundingSpreadCurve,
) -> tuple[float, ...]:
    """Positive PV funding costs from deterministic spreads and expected amount profiles."""
    _validate(times, amounts, discount)
    if not isinstance(spread, FundingSpreadCurve) or spread.times[-1] < times[-1]:
        raise DomainValidationError("Funding spread must cover profile horizon")
    nodes = _grid(times, discount.times, spread.times)
    values = tuple(product(discount.discount(t), _linear(times, amounts, t)) for t in nodes)
    return tuple(
        product(total((va * 0.5, vb * 0.5)), b - a, spread.spread(a))
        for a, b, va, vb in zip(nodes, nodes[1:], values, values[1:], strict=False)
    )


def _validate(times: tuple[float, ...], values: tuple[float, ...], discount: DiscountCurve) -> None:
    validate_times(times)
    magnitudes(values, len(times), "expected currency amount")
    if not isinstance(discount, DiscountCurve) or discount.day_count != DayCount.ACT_365_FIXED:
        raise DomainValidationError("XVA discount curve must declare ACT/365F")
    if discount.times[-1] < times[-1]:
        raise DomainValidationError("XVA never extrapolates a discount curve")


def sampled_credit_loss(
    times: tuple[float, ...],
    defaults: ExposureAtDefault,
    discount: DiscountCurve,
    recovery: RecoveryAssumption,
) -> tuple[float, ...]:
    """Sample mean D(bucket)*LGD*EAD; no PD factor is applied a second time.

    Right-grid alive-collateral approximation inherited explicitly from Phase 6;
    no default-conditioned margin freeze/MPOR or discounted stochastic numeraire.
    """
    _validate(times, tuple(0.0 for _ in times), discount)
    if not isinstance(defaults, ExposureAtDefault) or not isinstance(recovery, RecoveryAssumption):
        raise DomainValidationError("Sampled credit requires typed EAD and recovery")
    count = len(defaults.default_times)
    if count == 0 or len(defaults.bucket_times) != count:
        raise DomainValidationError("Sampled defaults must align with paths")
    magnitudes(defaults.positive_exposures, count, "sampled exposure")
    grouped: list[list[float]] = [[] for _ in times[1:]]
    for tau, bucket, exposure in zip(
        defaults.default_times, defaults.bucket_times, defaults.positive_exposures, strict=True
    ):
        if tau is None:
            if bucket is not None or exposure != 0:
                raise DomainValidationError("Nondefaults must have zero exposure and no bucket")
        else:
            tau = require_finite(tau, name="sampled default time")
            if not 0 < tau <= times[-1] or bucket != times[bisect_left(times, tau)]:
                raise DomainValidationError("Default bucket must be the first grid point >= tau")
            assert bucket is not None
            grouped[bisect_left(times, bucket) - 1].append(
                product(discount.discount(bucket), recovery.loss_given_default, exposure, 1 / count)
            )
    return tuple(total(tuple(values)) for values in grouped)


def calculate(
    profile: ExposureProfile,
    discount: DiscountCurve,
    counterparty: PiecewiseHazardCurve,
    recovery: RecoveryAssumption,
    own: OwnCredit,
    funding: FundingTerms,
    margin: MarginProfile,
    *,
    sampled_defaults: ExposureAtDefault | None = None,
) -> XvaResult:
    """Signed additive adjustments under explicit independent or sampled credit policy.

    DVA is unilateral own credit against ENE magnitude, not first-to-default bilateral.
    FVA uses E+/E- borrowing/lending proxies without default termination; MVA uses
    supplied segregated posted IM, separately, without double counting it in FVA.
    """
    if (
        not isinstance(profile, ExposureProfile)
        or not isinstance(own, OwnCredit)
        or not isinstance(funding, FundingTerms)
        or not isinstance(margin, MarginProfile)
    ):
        raise DomainValidationError("XVA needs validated exposure, own credit, funding and margin")
    _validate(profile.times, profile.expected_exposure, discount)
    _validate(profile.times, profile.expected_negative_exposure, discount)
    if (
        discount.currency != profile.currency
        or margin.currency != profile.currency
        or margin.times != profile.times
    ):
        raise DomainValidationError("XVA reporting currency and margin grid must match")
    if (
        not isinstance(counterparty, PiecewiseHazardCurve)
        or not isinstance(recovery, RecoveryAssumption)
        or counterparty.times[-1] < profile.times[-1]
    ):
        raise DomainValidationError("Counterparty credit must cover the finite profile")
    ee, ene, times = profile.expected_exposure, profile.expected_negative_exposure, profile.times
    cva = (
        credit_integral(times, ee, discount, counterparty, recovery)
        if sampled_defaults is None
        else sampled_credit_loss(times, sampled_defaults, discount, recovery)
    )
    dva = credit_integral(times, ene, discount, own.hazard, own.recovery)
    # A common refinement keeps FVA interval-level costs and benefits aligned.
    funding_grid = _grid(times, discount.times, funding.borrowing.times, funding.lending.times)
    funding_ee = tuple(_linear(times, ee, t) for t in funding_grid)
    funding_ene = tuple(_linear(times, ene, t) for t in funding_grid)
    fca = funding_integral(funding_grid, funding_ee, discount, funding.borrowing)
    raw_fba = funding_integral(funding_grid, funding_ene, discount, funding.lending)
    fba = raw_fba if funding.include_lending_benefit else tuple(0.0 for _ in raw_fba)
    mva = funding_integral(times, margin.posted_initial_margin, discount, funding.margin)
    credit_method = (
        "independent_D_EE_endpoint_average_exact_PD_increments"
        if sampled_defaults is None
        else "sampled_default_right_grid_alive_collateral_no_freeze_MPOR"
    )
    evidence = input_evidence(
        profile, discount, counterparty, recovery, own, funding, margin, sampled_defaults
    )
    digest = content_hash(evidence)
    methods = (
        credit_method,
        "unilateral_own_credit_independent_D_ENE_PD",
        "additive_alive_residual_funding_proxy_no_default_termination",
        "external_segregated_posted_IM_funding_no_default_termination",
    )
    signed = (
        tuple(-v for v in cva),
        dva,
        tuple(total((-a, b)) for a, b in zip(fca, fba, strict=True)),
        tuple(-v for v in mva),
    )
    grids = (
        _grid(times, discount.times, counterparty.times) if sampled_defaults is None else times,
        _grid(times, discount.times, own.hazard.times),
        funding_grid,
        _grid(times, discount.times, funding.margin.times),
    )
    components = tuple(
        XvaComponent(
            kind,
            priced_money(total(values), profile.currency),
            values,
            method,
            digest,
            tuple(f"({a},{b}] ACT/365F years" for a, b in zip(grid, grid[1:], strict=False)),
        )
        for kind, values, method, grid in zip(ComponentKind, signed, methods, grids, strict=True)
    )
    return XvaResult(
        profile.currency,
        components,
        priced_money(total(fca), profile.currency),
        priced_money(total(fba), profile.currency),
        digest,
        tuple(evidence.items()),
        (
            "Unilateral CVA/DVA are additive; no first-to-default bilateral recursion",
            "Deterministic reporting discount curve; no stochastic discount/exposure covariance",
            "Linear amount profiles and endpoint-average discounted quadrature on knot union",
            "Funding excess spreads apply to alive residual proxies without termination or hedges",
            "External segregated posted IM is separate from reusable CSA independent amount",
            "No regulatory IM model, recursive funding price or institutional calibration approval",
        ),
    )


def input_evidence(
    profile: ExposureProfile,
    discount: DiscountCurve,
    counterparty: PiecewiseHazardCurve,
    recovery: RecoveryAssumption,
    own: OwnCredit,
    funding: FundingTerms,
    margin: MarginProfile,
    sampled_defaults: ExposureAtDefault | None,
) -> dict[str, str]:
    """Canonical input/assumption identity, shared by calculator and port verification."""
    return {
        "profile": content_hash(
            (
                profile.currency,
                profile.times,
                profile.expected_exposure,
                profile.expected_negative_exposure,
            )
        ),
        "discount": discount.curve_hash,
        "counterparty": content_hash((counterparty, recovery)),
        "own": content_hash(own),
        "funding": content_hash(funding),
        "margin": content_hash(margin),
        "sampled_defaults": content_hash(sampled_defaults),
        "credit_method": "independent_D_EE_endpoint_average_exact_PD_increments"
        if sampled_defaults is None
        else "sampled_default_right_grid_alive_collateral_no_freeze_MPOR",
    }
