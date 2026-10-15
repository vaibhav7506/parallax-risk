"""Independent-credit XVA CVA quadrature challenger and ordered factor search mapping."""

from dataclasses import dataclass

from scipy.integrate import quad

from parallax_risk.application.validation_models import ProductionXvaModel
from parallax_risk.application.validation_stress import factor_unit
from parallax_risk.application.xva_revaluation import XvaExperiment, XvaRevaluation
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve
from parallax_risk.domain.exposure.contracts import DependenceKind
from parallax_risk.domain.market.curves.interpolation import LinearInterpolator
from parallax_risk.domain.pricing._numbers import total
from parallax_risk.domain.validation.contracts import Metric, ModelOutput
from parallax_risk.domain.validation.search import SearchDimension
from parallax_risk.domain.xva.risk import RiskFactor


@dataclass(frozen=True, slots=True)
class XvaCvaProduction:
    model: ProductionXvaModel

    def evaluate(self, case: XvaExperiment) -> ModelOutput:
        output = self.model.evaluate(case)
        return ModelOutput(
            output.case_hash,
            output.model_name,
            output.model_version,
            (output.metric("CVA"),),
            output.evidence_hash,
            output.assumptions,
        )


@dataclass(frozen=True, slots=True)
class IndependentCreditCvaChallenger:
    workflow: XvaRevaluation

    def evaluate(self, case: XvaExperiment) -> ModelOutput:
        if not isinstance(case, XvaExperiment) or any(
            c.kind != DependenceKind.INDEPENDENT for c in case.credit
        ):
            raise DomainValidationError("Quadrature challenger supports independent credit only")
        paths = self.workflow.exposure.run(
            case.request,
            case.book,
            case.markets,
            case.run,
            accounts=case.accounts,
            credit=case.credit,
        )
        losses = []
        for c, p in zip(case.credit, paths.counterparties, strict=True):
            if c.counterparty_id != p.counterparty_id:
                raise DomainValidationError("Credit/exposure counterparty order does not match")
            times = p.profile.times
            nodes = tuple(
                sorted(
                    set(times)
                    | {t for t in c.baseline.times if t <= times[-1]}
                    | {t for t in case.discount.times if t <= times[-1]}
                )
            )
            for a, b in zip(nodes, nodes[1:], strict=False):
                midpoint = (a + b) / 2
                index = next(
                    i
                    for i, (left, right) in enumerate(
                        zip(c.baseline.times, c.baseline.times[1:], strict=False)
                    )
                    if left <= midpoint < right
                )
                hazard = c.baseline.hazards[index]

                def integrand(
                    t: float,
                    times: tuple[float, ...] = times,
                    exposures: tuple[float, ...] = p.profile.expected_exposure,
                    curve: PiecewiseHazardCurve = c.baseline,
                    hazard: float = hazard,
                    lgd: float = c.recovery.loss_given_default,
                ) -> float:
                    ee = LinearInterpolator().interpolate(t, times, exposures)
                    return require_finite(
                        ee * case.discount.discount(t) * curve.survival(t) * hazard * lgd,
                        name="challenger CVA integrand",
                    )

                loss, error = quad(integrand, a, b, epsabs=1e-10, epsrel=1e-10)
                if (
                    not 0
                    <= require_finite(error, name="quadrature error")
                    <= 1e-9 * max(1.0, abs(loss))
                ):
                    raise DomainValidationError(
                        "Independent XVA quadrature failed its error criterion"
                    )
                losses.append(require_finite(loss, name="challenger CVA loss"))
        metric = Metric("CVA", -total(tuple(losses)), case.book.reporting_currency.value)
        return ModelOutput(
            case.hash,
            "independent-credit-quadrature",
            "0.10.0",
            (metric,),
            content_hash((case.hash, paths.positive_paths.hash, metric)),
            (
                "Shared exposure simulation; independent continuous D*linear-EE*survival*hazard",
                "Independent credit only; shared pricing/exposure bugs are outside this challenge",
                "ACT/365F grid; deterministic discount; signed CVA; no event likelihood",
            ),
        )


@dataclass(frozen=True, slots=True)
class XvaSearchCases:
    """Ordered absolute DELTAS from a fixed experiment; not level coordinates."""

    workflow: XvaRevaluation
    baseline: XvaExperiment
    factors: tuple[RiskFactor, ...]
    dimensions: tuple[SearchDimension, ...]

    def __post_init__(self) -> None:
        require_tuple(self.factors, RiskFactor, nonempty=True)
        require_tuple(self.dimensions, SearchDimension, nonempty=True)
        if (
            not isinstance(self.baseline, XvaExperiment)
            or len(self.factors) != len(self.dimensions)
            or len(set(self.factors)) != len(self.factors)
            or len({d.name for d in self.dimensions}) != len(self.dimensions)
        ):
            raise DomainValidationError("XVA search needs distinct aligned factors and baseline")
        if any(
            d.unit != factor_unit(f) for d, f in zip(self.dimensions, self.factors, strict=True)
        ):
            raise DomainValidationError("XVA search coordinates require exact absolute delta units")

    def __call__(self, parameters: tuple[float, ...]) -> XvaExperiment:
        if not isinstance(parameters, tuple) or len(parameters) != len(self.factors):
            raise DomainValidationError("XVA search parameters do not match factors")
        changed = self.baseline
        for d, f, value in zip(self.dimensions, self.factors, parameters, strict=True):
            if not d.lower <= require_finite(value, name="absolute factor delta") <= d.upper:
                raise DomainValidationError("Factor delta exceeds its declared search bound")
            changed = self.workflow.bump(changed, f, value)
        return changed
