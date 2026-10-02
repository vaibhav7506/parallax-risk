from dataclasses import replace
from datetime import date

import pytest

from parallax_risk.common.enums import Currency, DayCount
from parallax_risk.common.errors import NumericalError
from parallax_risk.common.identifiers import QuoteId
from parallax_risk.domain.market.curves.bootstrap import ParSwapQuote
from tests.fixtures.deterministic import YEAR_ONE, YEAR_TWO, flat_curve


def test_par_swap_annuity_does_not_silently_turn_infinite_inputs_into_zero_rate():
    quote = ParSwapQuote(
        QuoteId("extreme-swap"), Currency.USD, (YEAR_ONE, YEAR_TWO), 0.05, DayCount.ACT_365_FIXED
    )
    curve = replace(flat_curve(), discount_factors=(1.0, 1e308, 1e308))
    with pytest.raises(NumericalError, match="annuity"):
        quote.model_rate(curve)
    long_quote = replace(quote, payment_dates=(date(2027, 1, 1),))
    with pytest.raises(NumericalError, match="contribution"):
        long_quote.model_rate(curve)
