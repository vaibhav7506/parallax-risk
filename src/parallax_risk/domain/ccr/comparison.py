"""Exact component bridge and caller-specified illustrative capital inputs/exceptions."""

from dataclasses import dataclass
from decimal import Decimal

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain.ccr.challenger import ChallengerResult
from parallax_risk.domain.ccr.contracts import ComparisonPolicy
from parallax_risk.domain.ccr.standardized import StandardizedResult
from parallax_risk.domain.pricing._numbers import money_value, priced_money, product


@dataclass(frozen=True, slots=True)
class CapitalInputs:
    ead: Money
    illustrative_rwa: Money
    illustrative_capital: Money


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    standardized: StandardizedResult
    challenger: ChallengerResult
    policy_hash: str
    standardized_capital: CapitalInputs
    challenger_capital: CapitalInputs
    ead_difference: Money
    rwa_difference: Money
    capital_difference: Money
    relative_ead_difference: float | None
    exception: bool
    component_bridge: tuple[tuple[str, Money], ...]
    bridge_residual: Money
    interpretation: str = (
        "IMM challenger minus SA-CCR-inspired; illustrative capital; no compliance claim"
    )


def compare(
    standard: StandardizedResult, internal: ChallengerResult, policy: ComparisonPolicy
) -> ComparisonResult:
    if (
        not isinstance(standard, StandardizedResult)
        or not isinstance(internal, ChallengerResult)
        or not isinstance(policy, ComparisonPolicy)
    ):
        raise DomainValidationError("Comparison requires typed calculation results and policy")
    if (
        standard.scope != internal.scope
        or standard.currency != internal.currency
        or standard.currency != policy.currency
    ):
        raise DomainValidationError("Compare only matching legal scopes and reporting currencies")
    if internal.alpha != policy.challenger_alpha:
        raise DomainValidationError("Challenger alpha must match comparison policy")

    def capital(ead: Money) -> CapitalInputs:
        if ead.amount < 0 or ead.currency != policy.currency:
            raise DomainValidationError("Capital input EAD must be nonnegative reporting Money")
        rwa = product(money_value(ead), policy.risk_weight)
        return CapitalInputs(
            ead,
            priced_money(rwa, policy.currency),
            priced_money(product(rwa, policy.capital_ratio), policy.currency),
        )

    sa, imm = capital(standard.ead), capital(internal.ead)
    difference = internal.ead - standard.ead
    relative = (
        require_finite(
            money_value(difference) / money_value(standard.ead), name="relative EAD difference"
        )
        if standard.ead.amount > 0
        else None
    )
    exception = abs(difference.amount) > policy.absolute_tolerance.amount and (
        relative is None or abs(relative) > policy.relative_tolerance
    )
    rc = priced_money(
        product(standard.alpha, money_value(standard.replacement_cost)), policy.currency
    )
    pfe = priced_money(
        product(standard.alpha, money_value(standard.potential_future_exposure)), policy.currency
    )
    bridge = (
        ("internal_effective_epe", internal.ead),
        ("replacement_cost", -rc),
        ("standardized_pfe", -pfe),
        ("margin_cap", standard.uncapped_ead - standard.ead),
    )
    explained = sum((v for _, v in bridge), Money(Decimal(0), policy.currency))
    return ComparisonResult(
        standard,
        internal,
        content_hash(policy),
        sa,
        imm,
        difference,
        imm.illustrative_rwa - sa.illustrative_rwa,
        imm.illustrative_capital - sa.illustrative_capital,
        relative,
        exception,
        bridge,
        difference - explained,
    )
