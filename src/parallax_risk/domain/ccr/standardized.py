"""Restricted linear IR/FX SA-CCR-inspired formulas, with margined/unmargined cap."""

import math
from dataclasses import dataclass, replace

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.domain.ccr.contracts import AssetClass, StandardizedInputs, SupervisoryParameters
from parallax_risk.domain.pricing._numbers import money_value, priced_money, product, total


@dataclass(frozen=True, slots=True)
class TradeContribution:
    trade_id: str
    asset_class: AssetClass
    hedging_set: tuple[Currency, ...]
    bucket: int
    adjusted_notional: float
    maturity_factor: float
    effective_notional: float


@dataclass(frozen=True, slots=True)
class AddOnContribution:
    asset_class: AssetClass
    hedging_set: tuple[Currency, ...]
    bucket: int
    net_effective_notional: float
    add_on: float


@dataclass(frozen=True, slots=True)
class StandardizedResult:
    scope: str
    currency: Currency
    input_hash: str
    parameter_hash: str
    trade_contributions: tuple[TradeContribution, ...]
    add_on_contributions: tuple[AddOnContribution, ...]
    replacement_cost: Money
    aggregate_add_on: Money
    multiplier: float
    potential_future_exposure: Money
    alpha: float
    uncapped_ead: Money
    unmargined_ead_cap: Money | None
    ead: Money
    methodology: str = "restricted_linear_ir_fx_no_cross_ir_bucket_offsets_v0.8.0"


def standardized(
    inputs: StandardizedInputs, parameters: SupervisoryParameters
) -> StandardizedResult:
    """No offset across IR buckets, currencies or asset classes; full within-bucket offset."""
    if not isinstance(inputs, StandardizedInputs) or not isinstance(
        parameters, SupervisoryParameters
    ):
        raise DomainValidationError("Standardized CCR requires validated inputs and parameters")
    if (
        inputs.margin is not None
        and inputs.margin.margin_period_business_days < parameters.minimum_horizon_business_days
    ):
        raise DomainValidationError("Explicit MPOR must meet the configured business-day floor")
    contributions: list[TradeContribution] = []
    groups: dict[tuple[AssetClass, tuple[Currency, ...], int], list[float]] = {}
    for trade in inputs.trades:
        notional = money_value(trade.notional)
        bucket = 0
        if trade.asset_class == AssetClass.INTEREST_RATE:
            decay = parameters.duration_decay
            duration = (
                product(
                    math.exp(-product(decay, trade.start)),
                    -math.expm1(-product(decay, trade.end - trade.start)),
                )
                / decay
            )
            duration = max(
                require_finite(duration, name="supervisory duration"),
                parameters.minimum_horizon_business_days / parameters.business_days_per_year,
            )
            notional = product(notional, duration)
            bucket = 1 if trade.end < 1 else 2 if trade.end <= 5 else 3
        if inputs.margin is None:
            maturity_factor = math.sqrt(
                min(
                    1.0,
                    max(
                        trade.maturity,
                        parameters.minimum_horizon_business_days
                        / parameters.business_days_per_year,
                    ),
                )
            )
        else:
            maturity_factor = product(
                1.5,
                math.sqrt(
                    inputs.margin.margin_period_business_days / parameters.business_days_per_year
                ),
            )
        effective = product(notional, maturity_factor, trade.delta)
        # Orient FX delta relative to the first alphabetically ordered currency.
        currencies = tuple(sorted(trade.currencies))
        if trade.currencies != currencies:
            effective = -effective
        contributions.append(
            TradeContribution(
                str(trade.trade_id),
                trade.asset_class,
                currencies,
                bucket,
                notional,
                maturity_factor,
                effective,
            )
        )
        groups.setdefault((trade.asset_class, currencies, bucket), []).append(effective)
    add_ons = tuple(
        AddOnContribution(
            asset,
            currencies,
            bucket,
            total(tuple(values)),
            product(
                abs(total(tuple(values))),
                parameters.interest_rate_factor
                if asset == AssetClass.INTEREST_RATE
                else parameters.fx_factor,
            ),
        )
        for (asset, currencies, bucket), values in sorted(groups.items())
    )
    add_on = total(tuple(v.add_on for v in add_ons))
    net = total((money_value(inputs.value), -money_value(inputs.collateral)))
    buffer = 0.0
    if inputs.margin is not None:
        buffer = total(
            (
                money_value(inputs.margin.threshold),
                money_value(inputs.margin.minimum_transfer_amount),
                -money_value(inputs.margin.net_independent_collateral),
            )
        )
    rc = max(net, buffer, 0.0)
    multiplier = 1.0
    if add_on > 0 and net < 0:
        # Divide before scaling: avoids overflowing 2*(1-floor)*AddOn.
        exponent = require_finite(
            (net / add_on) / (2 * (1 - parameters.multiplier_floor)), name="multiplier exponent"
        )
        # exp(-large) may round to zero: the well-defined asymptotic multiplier floor.
        multiplier = total(
            (parameters.multiplier_floor, (1 - parameters.multiplier_floor) * math.exp(exponent))
        )
    pfe = product(multiplier, add_on)
    uncapped = product(parameters.alpha, total((rc, pfe)))
    cap = None
    if inputs.margin is not None:
        cap = standardized(replace(inputs, margin=None), parameters).ead
    currency = inputs.value.currency
    ead = min(uncapped, money_value(cap)) if cap is not None else uncapped
    return StandardizedResult(
        inputs.scope,
        currency,
        content_hash(inputs),
        content_hash(parameters),
        tuple(contributions),
        add_ons,
        priced_money(rc, currency),
        priced_money(add_on, currency),
        multiplier,
        priced_money(pfe, currency),
        parameters.alpha,
        priced_money(uncapped, currency),
        cap,
        priced_money(ead, currency),
    )
