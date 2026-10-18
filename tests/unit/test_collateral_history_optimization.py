"""Financial equivalence of cumulative history to the original independent rebuild."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from parallax_risk.application.service_examples import commands
from parallax_risk.application.workflows import Operation
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CollateralMovementId
from parallax_risk.common.money import Money
from parallax_risk.domain.portfolio.collateral import (
    CollateralMovement,
    collateral_value,
    validate_account,
)
from parallax_risk.domain.portfolio.csa import CollateralDirection


def reference(account, csa, market):
    for day in sorted({account.opening_date, *(m.settlement_date for m in account.movements)}):
        collateral_value(account.balances(day), csa, market)


@pytest.mark.parametrize("lag", [0, 2])
@pytest.mark.parametrize("direction", list(CollateralDirection))
@pytest.mark.parametrize("invalid", [False, True])
def test_every_historical_state_and_same_day_settlements_remain_validated(lag, direction, invalid):
    command = commands(2)[Operation.PORTFOLIO]
    csa = replace(
        command.book.counterparties[0].netting_sets[0].csa,
        direction=direction,
        settlement_lag_days=lag,
    )
    account = command.accounts[0]
    sign = -1 if direction == CollateralDirection.POST_ONLY else 1
    movements = []
    for i in range(20):
        day = account.opening_date + timedelta(days=i // 2)
        amount = sign * (10 if i % 2 == 0 else -9)
        if invalid and direction != CollateralDirection.TWO_WAY and i == 5:
            amount = -sign * 1000
        movements.append(
            CollateralMovement(
                CollateralMovementId(str(i)),
                day,
                day + timedelta(days=lag),
                Money(Decimal(amount), Currency.USD),
            )
        )
    account = replace(account, movements=tuple(movements))
    if invalid and direction != CollateralDirection.TWO_WAY:
        for validator in (reference, validate_account):
            with pytest.raises(DomainValidationError):
                validator(account, csa, command.market)
    else:
        assert reference(account, csa, command.market) is None
        assert validate_account(account, csa, command.market) is None
