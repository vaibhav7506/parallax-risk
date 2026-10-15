"""Labelled synthetic, reproducible Phase 10 evidence; no approval or market history."""

import math
from dataclasses import dataclass, replace
from datetime import date

from parallax_risk.application.validation_forensics import Counterfactual, DiagnosticState, diagnose
from parallax_risk.application.validation_models import ProductionCvaModel
from parallax_risk.application.validation_mutation import campaign
from parallax_risk.application.validation_probes import OperationProbeModel, ProbeCase, probe_suite
from parallax_risk.application.validation_search import SearchOptimizer, search
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.domain.simulation.random import StreamKey
from parallax_risk.domain.validation.benchmark import CvaBenchmarkCase, IndependentCvaBenchmark
from parallax_risk.domain.validation.contracts import Metric, Tolerance
from parallax_risk.domain.validation.forensics import CauseKind, DiagnosticContext, ForensicReport
from parallax_risk.domain.validation.mutation import Mutation, MutationCampaign, MutationKind
from parallax_risk.domain.validation.search import (
    LinearRestriction,
    SearchDimension,
    SearchResult,
    SearchSpec,
)


def probe_case() -> ProbeCase:
    return ProbeCase(
        CvaBenchmarkCase((0.0, 0.5, 1.0), (20.0, 100.0, 180.0), Currency.USD, 0.03, 0.2, 0.4),
        date(2025, 1, 1),
        date(2026, 1, 1),
        1.2,
        0.4,
        20.0,
        10.0,
        0.2,
        10,
        (1.0, 2.0, 4.0, 8.0),
        (date(2024, 12, 1), date(2025, 2, 1)),
        (0.2, 0.5),
        date(2025, 1, 1),
    )


def probe_targets(case: ProbeCase) -> tuple[Metric, ...]:
    """Independent hand formulas for these operation observables; not copied model output."""
    c = case.cva
    losses = tuple(
        (1 - c.recovery)
        * (ea * math.exp(-c.rate * a) + eb * math.exp(-c.rate * b))
        / 2
        * math.exp(-c.hazard * a)
        * (-math.expm1(-c.hazard * (b - a)))
        for a, b, ea, eb in zip(c.times, c.times[1:], c.exposure, c.exposure[1:], strict=False)
    )
    mean = math.fsum(case.samples) / len(case.samples)
    sem = math.sqrt(
        math.fsum((x - mean) ** 2 for x in case.samples)
        / (len(case.samples) - 1)
        / len(case.samples)
    )
    known = tuple(
        h
        for d, h in zip(case.calibration_dates, case.calibrated_hazards, strict=True)
        if d <= case.as_of
    )
    values = (
        (MutationKind.DISCOUNT, math.exp(-c.rate * c.times[-1]), "discount_factor"),
        (MutationKind.SIGN, -math.fsum(losses), c.currency.value),
        (MutationKind.RECOVERY, 1 - c.recovery, "LGD_fraction"),
        (MutationKind.FX, 100 * case.fx, c.currency.value),
        (MutationKind.DAY_COUNT, (case.end - case.start).days / 365, "years"),
        (MutationKind.CORRELATION, case.correlation, "correlation"),
        (MutationKind.COLLATERAL, max(c.exposure[-1] - case.collateral, 0.0), c.currency.value),
        (MutationKind.THRESHOLD, max(c.exposure[-1] - case.threshold, 0.0), c.currency.value),
        (MutationKind.DATE, c.exposure[-1], c.currency.value),
        (MutationKind.LOOK_AHEAD, known[-1], "annual_hazard"),
        (MutationKind.VOLATILITY, case.volatility * 100, "currency_per_sqrt_year"),
        (MutationKind.PATHS, sem, "sample_mean_standard_error"),
        (MutationKind.INTERPOLATION, 0.9, "discount_factor"),
        (
            MutationKind.MPOR,
            1.5 * math.sqrt(case.mpor_business_days / 250),
            "margin_maturity_factor",
        ),
        (
            MutationKind.DEFAULT,
            math.exp(-c.hazard * c.times[-2])
            * (-math.expm1(-c.hazard * (c.times[-1] - c.times[-2]))),
            "interval_default_probability",
        ),
    )
    return tuple(Metric(str(k), float(v), u) for k, v, u in values)


def mutations() -> tuple[Mutation, ...]:
    categories = {
        MutationKind.DISCOUNT: "valuation",
        MutationKind.SIGN: "valuation",
        MutationKind.RECOVERY: "credit",
        MutationKind.FX: "valuation",
        MutationKind.DAY_COUNT: "time",
        MutationKind.CORRELATION: "dependence",
        MutationKind.COLLATERAL: "collateral",
        MutationKind.THRESHOLD: "collateral",
        MutationKind.DATE: "time",
        MutationKind.LOOK_AHEAD: "calibration",
        MutationKind.VOLATILITY: "simulation",
        MutationKind.PATHS: "simulation",
        MutationKind.INTERPOLATION: "valuation",
        MutationKind.MPOR: "collateral",
        MutationKind.DEFAULT: "credit",
    }
    descriptions = (
        "Reverse discount exponent",
        "Reverse signed unilateral CVA",
        "Use recovery as LGD",
        "Invert declared direct FX conversion",
        "Use ACT/360 instead of ACT/365F",
        "Reverse Brownian correlation sign",
        "Omit held cash",
        "Omit CSA receive threshold",
        "Select prior exposure node",
        "Select future supplied calibration observation",
        "Treat decimal volatility as percent",
        "Use only first two supplied IID units",
        "Linear instead of log-linear positive ordinates",
        "Zero the MPOR maturity factor",
        "Cumulative PD instead of interval default mass",
    )
    return tuple(
        Mutation(str(k), k, categories[k], description)
        for k, description in zip(MutationKind, descriptions, strict=True)
    )


def cva_state(case: CvaBenchmarkCase) -> DiagnosticState[CvaBenchmarkCase]:
    absent = content_hash(
        "Explicitly absent: no calibration or collateral in this synthetic CVA case"
    )
    return DiagnosticState(
        case,
        DiagnosticContext(
            content_hash(case.rate),
            content_hash(case.exposure),
            absent,
            content_hash((case.hazard, case.recovery)),
            content_hash(case.times),
            absent,
        ),
    )


@dataclass(frozen=True, slots=True)
class AdversarialResearch:
    probe: ProbeCase
    targets: tuple[Metric, ...]
    full_suite: MutationCampaign
    weak_suite: MutationCampaign
    search: SearchResult
    diagnostics: ForensicReport


def example(optimizer: SearchOptimizer) -> AdversarialResearch:
    case = probe_case()
    targets = probe_targets(case)
    tolerance = Tolerance(1e-10, 1e-12)
    model = OperationProbeModel()
    full = campaign(
        model,
        case,
        mutations(),
        lambda o: probe_suite(o, targets, tolerance),
        "python scripts/demo_adversarial.py",
    )
    weak = campaign(
        model,
        case,
        mutations(),
        lambda o: probe_suite(o, (targets[1],), tolerance),
        "Retained intentionally incomplete sign-only suite",
    )
    dimensions = (
        SearchDimension(
            "rate",
            "annual_decimal_rate",
            -0.01,
            0.08,
            "Synthetic continuously compounded research interval",
        ),
        SearchDimension(
            "hazard", "annual_hazard", 0.01, 0.5, "Synthetic nonnegative credit interval"
        ),
        SearchDimension(
            "recovery", "recovery_fraction", 0.1, 0.7, "Synthetic bounded recovery interval"
        ),
    )
    spec = SearchSpec(
        dimensions,
        (
            LinearRestriction(
                "rate-plus-hazard",
                (1.0, 1.0, 0.0),
                0.0,
                0.55,
                "Declared synthetic combined decay range",
            ),
        ),
        StreamKey(20261001, 1000, 0),
        "CVA",
        "Synthetic research bounds; not observed market ranges",
        2,
        3,
        27,
    )
    production = ProductionCvaModel()
    searched = search(
        production,
        IndependentCvaBenchmark(),
        lambda p: replace(case.cva, rate=p[0], hazard=p[1], recovery=p[2]),
        optimizer,
        spec,
    )
    rate_case = replace(case.cva, rate=0.05)
    recovery_case = replace(rate_case, recovery=0.3)
    changed = replace(recovery_case, exposure=tuple(1.2 * v for v in case.cva.exposure))
    diagnostics = diagnose(
        production,
        cva_state(case.cva),
        cva_state(changed),
        (
            Counterfactual("rate", CauseKind.MARKET, cva_state(rate_case)),
            Counterfactual("recovery", CauseKind.PARAMETERS, cva_state(recovery_case)),
        ),
        "CVA",
        Tolerance(0.1),
        Tolerance(1e-12),
        "Retain actual CVA before/after and ordered rate/recovery cases",
    )
    return AdversarialResearch(case, targets, full, weak, searched, diagnostics)
