"""Real scenario bump/repricing using owned common market/default/rank sequences."""

from dataclasses import dataclass, replace
from decimal import Decimal

from parallax_risk.application.context import RunContext
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.xva import XvaRunResult, XvaService
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_token, require_tuple
from parallax_risk.domain.credit.dependence import ReducedFormSpread
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.contracts import CreditScenario, DependenceKind
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario, component
from parallax_risk.domain.market.curves.term_structures import DiscountCurve
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.models.correlation import CorrelationMatrix
from parallax_risk.domain.models.rates import HullWhite, Vasicek
from parallax_risk.domain.portfolio.collateral import CollateralAccount
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.simulation.contracts import SimulationRequest
from parallax_risk.domain.xva.contracts import FundingTerms, MarginProfile, OwnCredit
from parallax_risk.domain.xva.risk import (
    FactorKind,
    RiskFactor,
    XvaAttribution,
    XvaSensitivity,
    attribute,
    sensitivity,
)


@dataclass(frozen=True, slots=True)
class XvaExperiment:
    """Full explicit scenario configuration; fixed funding/IM during listed market bumps."""

    request: SimulationRequest
    book: PortfolioSnapshot
    markets: ConditionalMarketScenario
    accounts: tuple[CollateralAccount, ...]
    credit: tuple[CreditScenario, ...]
    own: OwnCredit
    discount: DiscountCurve
    funding: FundingTerms
    margins: tuple[MarginProfile, ...]
    run: RunContext

    def __post_init__(self) -> None:
        for value, kind in (
            (self.request, SimulationRequest),
            (self.book, PortfolioSnapshot),
            (self.markets, ConditionalMarketScenario),
            (self.own, OwnCredit),
            (self.discount, DiscountCurve),
            (self.funding, FundingTerms),
            (self.run, RunContext),
        ):
            if not isinstance(value, kind):
                raise DomainValidationError("XVA experiment requires validated typed inputs")
        require_tuple(self.accounts, CollateralAccount)
        require_tuple(self.credit, CreditScenario, nonempty=True)
        require_tuple(self.margins, MarginProfile, nonempty=True)
        if self.markets.request != self.request:
            raise DomainValidationError("XVA market binding must use the same request")

    @property
    def hash(self) -> str:
        return content_hash(
            (
                self.request,
                self.book,
                self.markets.hash,
                self.accounts,
                tuple(c.hash for c in self.credit),
                self.own,
                self.discount,
                self.funding,
                self.margins,
                self.run,
            )
        )


@dataclass(frozen=True, slots=True)
class FactorMove:
    name: str
    factor: RiskFactor
    amount: float

    def __post_init__(self) -> None:
        require_token(self.name)
        if not isinstance(self.factor, RiskFactor):
            raise DomainValidationError("Factor movement requires a typed factor")
        require_finite(self.amount, name="factor movement")


@dataclass(frozen=True, slots=True)
class XvaRevaluation:
    exposure: ExposureService
    xva: XvaService

    def value(self, experiment: XvaExperiment) -> XvaRunResult:
        if not isinstance(experiment, XvaExperiment):
            raise DomainValidationError("Revaluation needs a complete XVA experiment")
        e = experiment
        paths = self.exposure.run(
            e.request, e.book, e.markets, e.run, accounts=e.accounts, credit=e.credit
        )
        return self.xva.value(paths, e.discount, e.credit, e.own, e.funding, e.margins, e.run)

    def bump(self, experiment: XvaExperiment, factor: RiskFactor, amount: float) -> XvaExperiment:
        """Absolute parameter bump; recovery holds baseline hazard fixed.

        Dynamic recovery/spread bumps update the explicit credit-triangle policy.
        Rate bumps shift initial/long-run forwards and consistent FX drift changes;
        reporting-currency discount zero rates shift too. Origin fixings stay fixed.
        """
        if not isinstance(experiment, XvaExperiment) or not isinstance(factor, RiskFactor):
            raise DomainValidationError("Bump needs experiment and exact factor")
        amount = require_finite(amount, name="factor movement")
        if amount == 0:
            return experiment
        e = experiment
        request, book, credit, discount = e.request, e.book, e.credit, e.discount
        components = list(request.components)
        if factor.kind in (FactorKind.RATE, FactorKind.FX, FactorKind.VOLATILITY):
            item, _ = component(request, factor.target)
            i = next(i for i, c in enumerate(components) if c.name == factor.target)
            process = item.process
            if factor.kind == FactorKind.VOLATILITY:
                if not isinstance(process, (Vasicek, HullWhite, GeometricBrownianMotion)):
                    raise DomainValidationError(
                        "Vega supports the declared rate/GBM volatility only"
                    )
                components[i] = replace(
                    item, process=replace(process, volatility=process.volatility + amount)
                )
            elif factor.kind == FactorKind.FX:
                if not any(b.component == factor.target for b in e.markets.fx):
                    raise DomainValidationError("FX delta requires a bound FX component")
                components[i] = replace(item, initial_state=(item.initial_state[0] + amount,))
            else:
                currencies = {b.currency for b in e.markets.rates if b.component == factor.target}
                if not currencies or not isinstance(process, (Vasicek, HullWhite)):
                    raise DomainValidationError("Rate delta requires a bound short-rate component")
                shifted = (
                    replace(process, level=process.level + amount)
                    if isinstance(process, Vasicek)
                    else replace(
                        process,
                        initial_curve=replace(
                            process.initial_curve, level=process.initial_curve.level + amount
                        ),
                    )
                )
                components[i] = replace(
                    item, process=shifted, initial_state=(item.initial_state[0] + amount,)
                )
                for binding in e.markets.fx:
                    fx_i = next(j for j, c in enumerate(components) if c.name == binding.component)
                    fx = components[fx_i]
                    assert isinstance(fx.process, GeometricBrownianMotion)
                    drift = amount * (
                        int(binding.quote in currencies) - int(binding.base in currencies)
                    )
                    components[fx_i] = replace(
                        fx, process=replace(fx.process, drift_rate=fx.process.drift_rate + drift)
                    )
                if discount.currency in currencies:
                    discount = discount.bumped(amount)
            request = replace(request, components=tuple(components))
        elif factor.kind in (FactorKind.CREDIT_SPREAD, FactorKind.RECOVERY):
            index = next(
                (i for i, c in enumerate(credit) if str(c.counterparty_id) == factor.target), None
            )
            if index is None:
                raise DomainValidationError(
                    "Credit bump target must identify an existing counterparty"
                )
            c = credit[index]
            if c.kind == DependenceKind.DYNAMIC_SPREAD:
                if type(c.spread_policy) is not ReducedFormSpread:
                    raise DomainValidationError(
                        "Dynamic credit bumps require the explicit credit-triangle policy"
                    )
                if factor.kind == FactorKind.CREDIT_SPREAD and any(
                    other.spread_component == c.spread_component
                    for i, other in enumerate(credit)
                    if i != index
                ):
                    raise DomainValidationError(
                        "Single-name credit spread bump cannot move a shared spread component"
                    )
            if factor.kind == FactorKind.RECOVERY:
                c = replace(
                    c,
                    recovery=RecoveryAssumption(c.recovery.fraction + amount),
                    spread_policy=ReducedFormSpread(
                        RecoveryAssumption(c.recovery.fraction + amount)
                    )
                    if c.kind == DependenceKind.DYNAMIC_SPREAD
                    else None,
                )
            else:
                if c.recovery.fraction == 1:
                    raise DomainValidationError(
                        "Credit-spread conversion requires recovery below one"
                    )
                c = replace(
                    c,
                    baseline=PiecewiseHazardCurve(
                        c.baseline.times,
                        tuple(
                            h + amount / c.recovery.loss_given_default for h in c.baseline.hazards
                        ),
                    ),
                )
                if c.kind == DependenceKind.DYNAMIC_SPREAD:
                    assert c.spread_component is not None
                    j = next(j for j, v in enumerate(components) if v.name == c.spread_component)
                    components[j] = replace(
                        components[j], initial_state=(components[j].initial_state[0] + amount,)
                    )
                    request = replace(request, components=tuple(components))
            credit = tuple(c if i == index else v for i, v in enumerate(credit))
        elif factor.kind == FactorKind.CORRELATION:
            assert factor.second is not None
            if (
                factor.target not in request.factor_names
                or factor.second not in request.factor_names
            ):
                raise DomainValidationError("Correlation pair must match exact driver names")
            first, second = (
                request.factor_names.index(factor.target),
                request.factor_names.index(factor.second),
            )
            n = request.driver_dimension
            matrix = (
                [list(row) for row in request.correlation.values]
                if request.correlation is not None
                else [[float(i == j) for j in range(n)] for i in range(n)]
            )
            matrix[first][second] += amount
            matrix[second][first] += amount
            request = replace(
                request,
                correlation=replace(request.correlation, values=tuple(tuple(row) for row in matrix))
                if request.correlation is not None
                else CorrelationMatrix(request.factor_names, tuple(tuple(row) for row in matrix)),
            )
        else:
            scope = next(
                (
                    n
                    for cp in book.counterparties
                    for n in cp.netting_sets
                    if str(n.netting_set_id) == factor.target
                ),
                None,
            )
            if scope is None or scope.csa is None:
                raise DomainValidationError("Collateral sensitivity needs an existing CSA scope")
            threshold = scope.csa.receive_threshold + Money(
                Decimal(str(amount)), scope.csa.currency
            )
            changed_scope = replace(scope, csa=replace(scope.csa, receive_threshold=threshold))
            book = replace(
                book,
                counterparties=tuple(
                    replace(
                        cp,
                        netting_sets=tuple(
                            changed_scope if n.netting_set_id == scope.netting_set_id else n
                            for n in cp.netting_sets
                        ),
                    )
                    for cp in book.counterparties
                ),
            )
        moved = replace(
            e,
            request=request,
            markets=replace(e.markets, request=request),
            book=book,
            credit=credit,
            discount=discount,
        )
        if moved.hash == e.hash:
            raise DomainValidationError("Factor bump is below input resolution")
        return moved

    def sensitivity(
        self, experiment: XvaExperiment, factor: RiskFactor, bump: float
    ) -> XvaSensitivity:
        units = {
            FactorKind.RATE: "reporting currency per decimal annual rate; zero/state shift",
            FactorKind.FX: "reporting currency per direct QUOTE/BASE spot unit",
            FactorKind.VOLATILITY: "reporting currency per declared model volatility unit",
            FactorKind.CREDIT_SPREAD: "currency per annual decimal credit-triangle spread",
            FactorKind.RECOVERY: "reporting currency per recovery fraction; baseline hazard fixed",
            FactorKind.CORRELATION: "reporting currency per Brownian correlation coefficient",
            FactorKind.COLLATERAL: "reporting currency per CSA receive-threshold currency unit",
        }
        if not isinstance(factor, RiskFactor):
            raise DomainValidationError("Sensitivity requires typed factor")
        return sensitivity(
            factor,
            bump,
            units[factor.kind],
            lambda amount: self.value(self.bump(experiment, factor, amount)).result,
        )

    def attribute(
        self, baseline: XvaExperiment, moves: tuple[FactorMove, ...], actual: XvaExperiment
    ) -> XvaAttribution:
        """Revalue ordered factors and independently value actual endpoint; residual not hidden."""
        require_tuple(moves, FactorMove)
        if len({move.name for move in moves}) != len(moves):
            raise DomainValidationError("Attribution movement names must be unique")
        start = self.value(baseline).result
        state = baseline
        ladder = []
        for move in moves:
            state = self.bump(state, move.factor, move.amount)
            ladder.append((move.name, self.value(state).result))
        return attribute(start, tuple(ladder), self.value(actual).result)
