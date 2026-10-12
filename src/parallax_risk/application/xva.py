"""Run-linked XVA orchestration with injected mathematics and legal-scope attribution."""

from dataclasses import dataclass
from typing import Protocol

from parallax_risk.application.context import RunContext
from parallax_risk.application.exposure import ExposureRunResult
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError, ParallaxError
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario, DependenceKind
from parallax_risk.domain.exposure.statistics import ExposureAtDefault, ExposureProfile
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.pricing._numbers import money_value, priced_money, total
from parallax_risk.domain.xva.calculators import calculate, input_evidence
from parallax_risk.domain.xva.contracts import (
    ComponentKind,
    CounterpartyXva,
    FundingTerms,
    MarginProfile,
    OwnCredit,
    XvaComponent,
    XvaResult,
)


class XvaCalculator(Protocol):
    def calculate(
        self,
        profile: ExposureProfile,
        discount: DiscountCurve,
        counterparty: PiecewiseHazardCurve,
        recovery: RecoveryAssumption,
        own: OwnCredit,
        funding: FundingTerms,
        margin: MarginProfile,
        *,
        sampled_defaults: ExposureAtDefault | None = None,
    ) -> XvaResult: ...


@dataclass(frozen=True, slots=True)
class AdditiveXvaCalculator:
    """Production domain calculator implementing the injected application port."""

    calculate = staticmethod(calculate)


@dataclass(frozen=True, slots=True)
class XvaRunResult:
    context: RunContext
    exposure_hash: str
    counterparties: tuple[CounterpartyXva, ...]
    result: XvaResult


@dataclass(frozen=True, slots=True)
class XvaService:
    calculator: XvaCalculator
    logger: WorkflowLogger

    def value(
        self,
        exposure: ExposureRunResult,
        discount: DiscountCurve,
        credit: tuple[CreditScenario, ...],
        own: OwnCredit,
        funding: FundingTerms,
        margins: tuple[MarginProfile, ...],
        run: RunContext,
    ) -> XvaRunResult:
        """Align ordered per-name credit/IM with exposure, reject stale/foreign evidence.

        Independent CVA uses deterministic increment integration; static/dynamic
        dependence uses the actual scenario's sampled defaults and bucket exposures.
        DVA stays explicitly independent own credit, with no first-to-default claim.
        """
        if not isinstance(run, RunContext):
            raise DomainValidationError("XVA requires validated run metadata")
        self.logger.event("xva_started", run_id=str(run.run_id), outcome="started")
        try:
            result = self._value(exposure, discount, credit, own, funding, margins, run)
        except ParallaxError as error:
            self.logger.event(
                "xva_failed",
                run_id=str(run.run_id),
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event("xva_completed", run_id=str(run.run_id), outcome="completed")
        return result

    def _value(
        self,
        exposure: ExposureRunResult,
        discount: DiscountCurve,
        credit: tuple[CreditScenario, ...],
        own: OwnCredit,
        funding: FundingTerms,
        margins: tuple[MarginProfile, ...],
        run: RunContext,
    ) -> XvaRunResult:
        if (
            not isinstance(exposure, ExposureRunResult)
            or exposure.context != run
            or not isinstance(discount, DiscountCurve)
        ):
            raise DomainValidationError(
                "XVA needs matching exposure/run and explicit discount curve"
            )
        require_tuple(credit, CreditScenario, nonempty=True)
        require_tuple(margins, MarginProfile, nonempty=True)
        if (
            len(credit) != len(exposure.counterparties)
            or len(margins) != len(credit)
            or discount.valuation_date != exposure.dates[0]
        ):
            raise DomainValidationError(
                "Supply one ordered credit/IM profile per counterparty at origin"
            )
        source = content_hash(
            (
                exposure.portfolio_hash,
                exposure.market_scenario_hash,
                exposure.market_path_digest,
                exposure.initial_account_hashes,
                exposure.positive_paths.hash,
                exposure.negative_paths.hash,
                exposure.simulation,
                exposure.context,
            )
        )
        names = []
        for cp, specification, margin in zip(exposure.counterparties, credit, margins, strict=True):
            if (
                cp.counterparty_id != specification.counterparty_id
                or cp.credit_hash != specification.hash
                or cp.default_comparison is None
            ):
                raise DomainValidationError(
                    "XVA credit must match the exact exposure scenario's evidence"
                )
            sampled = (
                cp.default_comparison.scenario
                if specification.kind != DependenceKind.INDEPENDENT
                else None
            )
            result = self.calculator.calculate(
                cp.profile,
                discount,
                specification.baseline,
                specification.recovery,
                own,
                funding,
                margin,
                sampled_defaults=sampled,
            )
            if (
                not isinstance(result, XvaResult)
                or result.currency != exposure.total_profile.currency
            ):
                raise DomainValidationError("XVA calculator returned invalid result/currency")
            evidence = input_evidence(
                cp.profile,
                discount,
                specification.baseline,
                specification.recovery,
                own,
                funding,
                margin,
                sampled,
            )
            if dict(result.attribution) != evidence or result.input_hash != content_hash(evidence):
                raise DomainValidationError("XVA calculator returned stale/foreign input evidence")
            names.append(CounterpartyXva(cp.counterparty_id, result))
        currency = exposure.total_profile.currency
        digest = content_hash((source, tuple((n.counterparty_id, n.result.hash) for n in names)))
        components = tuple(
            XvaComponent(
                kind,
                priced_money(
                    total(tuple(money_value(n.result.component(kind).adjustment) for n in names)),
                    currency,
                ),
                tuple(money_value(n.result.component(kind).adjustment) for n in names),
                "sum_of_separate_counterparty_components; contributions_are_counterparty_totals",
                digest,
                tuple(str(n.counterparty_id) for n in names),
            )
            for kind in ComponentKind
        )
        aggregate = XvaResult(
            currency,
            components,
            priced_money(total(tuple(money_value(n.result.funding_cost) for n in names)), currency),
            priced_money(
                total(tuple(money_value(n.result.funding_benefit) for n in names)), currency
            ),
            digest,
            (("exposure", source), *((str(n.counterparty_id), n.result.input_hash) for n in names)),
            names[0].result.assumptions,
        )
        return XvaRunResult(run, source, tuple(names), aggregate)
