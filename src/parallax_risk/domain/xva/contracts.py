"""Validated finite-grid funding/margin inputs and signed XVA result evidence."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CounterpartyId
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_currency, require_text, require_tuple
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.exposure.statistics import validate_times
from parallax_risk.domain.pricing._numbers import money_value, priced_money, total


def magnitudes(values: tuple[float, ...], count: int, name: str) -> None:
    """Currency-unit nonnegative amounts; no clipping of invalid financial inputs."""
    if not isinstance(values, tuple) or len(values) != count:
        raise DomainValidationError(f"{name} must be an aligned immutable tuple")
    for value in values:
        if require_finite(value, name=name) < 0:
            raise DomainValidationError(f"{name} cannot be negative")


def fingerprint(value: str) -> None:
    """Require a declared lowercase SHA-256 content identifier."""
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise DomainValidationError("XVA evidence requires a SHA-256 fingerprint")


@dataclass(frozen=True, slots=True)
class FundingSpreadCurve:
    """Annual decimal spread, constant on [t_i,t_(i+1)); no extrapolation."""

    times: tuple[float, ...]
    spreads: tuple[float, ...]

    def __post_init__(self) -> None:
        validate_times(self.times)
        magnitudes(self.spreads, len(self.times) - 1, "funding spread")

    def spread(self, time: float) -> float:
        time = require_finite(time, name="funding time")
        if not 0 <= time <= self.times[-1]:
            raise DomainValidationError("Funding spread cannot be extrapolated")
        for end, spread in zip(self.times[1:], self.spreads, strict=True):
            if time < end:
                return spread
        return self.spreads[-1]


@dataclass(frozen=True, slots=True)
class MarginProfile:
    """Expected segregated posted IM in reporting currency; externally estimated."""

    currency: Currency
    times: tuple[float, ...]
    posted_initial_margin: tuple[float, ...]
    source: str

    def __post_init__(self) -> None:
        require_currency(self.currency)
        validate_times(self.times)
        magnitudes(self.posted_initial_margin, len(self.times), "posted initial margin")
        require_text(self.source)


@dataclass(frozen=True, slots=True)
class FundingTerms:
    """Additive alive-profile proxy; FVA=-FCA+FBA, with benefit explicitly enabled.

    Exposure residual is a declared borrowing/lending proxy, excluding segregated IM.
    Spreads are excess of the discount/collateral remuneration benchmark. No default
    termination, hedge cash, recursive funding equation or interest on VM is inferred.
    """

    borrowing: FundingSpreadCurve
    lending: FundingSpreadCurve
    margin: FundingSpreadCurve
    include_lending_benefit: bool

    def __post_init__(self) -> None:
        if not all(
            isinstance(v, FundingSpreadCurve) for v in (self.borrowing, self.lending, self.margin)
        ):
            raise DomainValidationError("Funding terms require three explicit spread curves")
        if type(self.include_lending_benefit) is not bool:
            raise DomainValidationError("Funding benefit policy must be explicit boolean")


@dataclass(frozen=True, slots=True)
class OwnCredit:
    """Own unilateral default curve/recovery, independent of market and counterparty."""

    hazard: PiecewiseHazardCurve
    recovery: RecoveryAssumption

    def __post_init__(self) -> None:
        if not isinstance(self.hazard, PiecewiseHazardCurve) or not isinstance(
            self.recovery, RecoveryAssumption
        ):
            raise DomainValidationError("Own credit needs explicit hazard and recovery")


class ComponentKind(StrEnum):
    CVA = "CVA"
    DVA = "DVA"
    FVA = "FVA"
    MVA = "MVA"


@dataclass(frozen=True, slots=True)
class XvaComponent:
    """Signed value contribution: CVA/MVA costs negative, DVA benefit positive."""

    kind: ComponentKind
    adjustment: Money
    contributions: tuple[float, ...]
    methodology: str
    input_hash: str
    contribution_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ComponentKind) or not isinstance(self.adjustment, Money):
            raise DomainValidationError("XVA component requires typed kind and Money")
        require_tuple(self.contributions, float, nonempty=True)
        require_text(self.methodology)
        fingerprint(self.input_hash)
        require_tuple(self.contribution_labels, str, nonempty=True)
        if len(self.contribution_labels) != len(self.contributions):
            raise DomainValidationError("Contribution labels must align with values")
        for label in self.contribution_labels:
            require_text(label)
        summed = total(self.contributions)
        if priced_money(summed, self.adjustment.currency) != self.adjustment:
            raise DomainValidationError("Component contributions do not reconcile")
        sign = 1 if self.kind == ComponentKind.DVA else -1
        if self.kind != ComponentKind.FVA and any(sign * value < 0 for value in self.contributions):
            raise DomainValidationError("Component contribution has inconsistent sign")


@dataclass(frozen=True, slots=True)
class XvaResult:
    """Four additive components; not a first-to-default or recursive replication price."""

    currency: Currency
    components: tuple[XvaComponent, ...]
    funding_cost: Money
    funding_benefit: Money
    input_hash: str
    attribution: tuple[tuple[str, str], ...]
    assumptions: tuple[str, ...]
    model_version: str = "0.7.0"

    def __post_init__(self) -> None:
        require_currency(self.currency)
        require_tuple(self.components, XvaComponent, nonempty=True)
        if tuple(c.kind for c in self.components) != tuple(ComponentKind):
            raise DomainValidationError("XVA requires CVA/DVA/FVA/MVA exactly once in order")
        if any(c.adjustment.currency != self.currency for c in self.components):
            raise DomainValidationError("XVA component currencies must match")
        for v in (self.funding_cost, self.funding_benefit):
            if not isinstance(v, Money) or v.currency != self.currency or money_value(v) < 0:
                raise DomainValidationError(
                    "Funding costs/benefits require nonnegative same-currency Money"
                )
        # Same binary64 reconciliation policy as all valuation results.
        fva = self.component(ComponentKind.FVA).adjustment
        expected = total((-money_value(self.funding_cost), money_value(self.funding_benefit)))
        if abs(money_value(fva) - expected) > 1e-12 * max(1.0, abs(expected)):
            raise DomainValidationError(
                "FVA must reconcile to -FCA+FBA within 1e-12 relative/absolute"
            )
        fingerprint(self.input_hash)
        if any(c.input_hash != self.input_hash for c in self.components):
            raise DomainValidationError("XVA component evidence must match result inputs")
        require_tuple(self.attribution, tuple)
        if any(len(pair) != 2 for pair in self.attribution):
            raise DomainValidationError("Attribution metadata must contain key/value pairs")
        for key, value in self.attribution:
            require_text(key)
            require_text(value)
        if len({key for key, _ in self.attribution}) != len(self.attribution):
            raise DomainValidationError("Attribution keys must be unique")
        require_tuple(self.assumptions, str, nonempty=True)
        for value in self.assumptions:
            require_text(value)
        require_text(self.model_version)

    def component(self, kind: ComponentKind) -> XvaComponent:
        for value in self.components:
            if value.kind == kind:
                return value
        raise DomainValidationError("Unknown XVA component")

    @property
    def total_adjustment(self) -> Money:
        return priced_money(
            total(tuple(money_value(c.adjustment) for c in self.components)), self.currency
        )

    @property
    def hash(self) -> str:
        return content_hash(self)


@dataclass(frozen=True, slots=True)
class CounterpartyXva:
    counterparty_id: CounterpartyId
    result: XvaResult
