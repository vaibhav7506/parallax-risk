"""Stateless deterministic cash-flow, bond, swap and deliverable FX-forward pricing."""

from dataclasses import dataclass
from datetime import date

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import NumericalError, PricingError
from parallax_risk.common.identifiers import ModelVersion
from parallax_risk.common.math import require_finite
from parallax_risk.common.money import Money
from parallax_risk.common.time import require_date
from parallax_risk.domain._validation import positive_accrual
from parallax_risk.domain.instruments.cashflows import (
    CashFlow,
    FixedRateCashFlow,
    FloatingRateCashFlow,
)
from parallax_risk.domain.instruments.fx.contracts import FxDirection, FxForward
from parallax_risk.domain.instruments.rates.contracts import (
    FixedRateBond,
    InterestRateSwap,
    SwapDirection,
    ZeroCouponBond,
)
from parallax_risk.domain.market.curves.term_structures import CurveSet
from parallax_risk.domain.market.observations import FxSpot
from parallax_risk.domain.market.snapshot import MarketSnapshot
from parallax_risk.domain.pricing._numbers import money_value, priced_money, product, total
from parallax_risk.domain.pricing.results import CashFlowPresentValue, PricingResult, RateOrigin

type Instrument = (
    CashFlow
    | FixedRateCashFlow
    | FloatingRateCashFlow
    | ZeroCouponBond
    | FixedRateBond
    | InterestRateSwap
    | FxForward
)


@dataclass(frozen=True, slots=True)
class PricingContext:
    """Snapshot and explicit curves; same-day payments excluded unless opted in."""

    snapshot: MarketSnapshot
    curves: CurveSet
    include_valuation_date_payments: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, MarketSnapshot) or not isinstance(self.curves, CurveSet):
            raise PricingError("Pricing context requires typed market snapshot and curve set")
        if type(self.include_valuation_date_payments) is not bool:
            raise PricingError("Same-day payment policy must be boolean")
        all_curves = (
            *self.curves.discount_curves,
            *(forward.curve for forward in self.curves.forward_curves),
        )
        if any(
            curve.valuation_date != self.snapshot.valuation_date
            or curve.currency not in self.snapshot.currencies
            for curve in all_curves
        ):
            raise PricingError("Curve dates/currencies must agree with market snapshot")

    def includes_payment(self, payment_date: date) -> bool:
        """Apply the declared settlement cutoff, without changing supplied dates."""
        require_date(payment_date)
        return payment_date > self.snapshot.valuation_date or (
            self.include_valuation_date_payments and payment_date == self.snapshot.valuation_date
        )


def _fx_conversion(spot: FxSpot, context: PricingContext) -> float:
    base = context.curves.discount_curve(spot.base_currency)
    quote = context.curves.discount_curve(spot.quote_currency)
    ratio = require_finite(
        quote.discount(spot.value_date) / base.discount(spot.value_date),
        name="spot settlement discount ratio",
    )
    if ratio <= 0:
        raise NumericalError("Spot settlement conversion underflowed")
    return product(spot.rate, ratio)


def forward_fx_rate(
    base_currency: Currency, quote_currency: Currency, maturity: date, context: PricingContext
) -> float:
    """Covered-interest-parity QUOTE/BASE forward for an explicitly settled spot.

    F(T) = S(s) * [Dq(s)/Db(s)] * [Db(T)/Dq(T)]. Curves represent a deterministic,
    frictionless common funding convention; cross-currency basis is unsupported.
    """
    require_date(maturity)
    spot = context.snapshot.fx_spot(base_currency, quote_currency)
    if maturity < spot.value_date:
        raise PricingError("FX forward maturity cannot precede the quoted spot value date")
    base_discount = context.curves.discount_curve(base_currency).discount(maturity)
    quote_discount = context.curves.discount_curve(quote_currency).discount(maturity)
    ratio = require_finite(base_discount / quote_discount, name="FX forward discount ratio")
    if ratio <= 0:
        raise NumericalError("FX forward ratio underflowed")
    return product(_fx_conversion(spot, context), ratio)


class DiscountingEngine:
    """Stateless deterministic model; all quantitative logic stays outside API/CLI."""

    def _payment(
        self,
        cashflow: CashFlow,
        context: PricingContext,
        origin: RateOrigin,
        *,
        result_currency: Currency | None = None,
        conversion: float = 1.0,
        coupon_rate: float | None = None,
    ) -> CashFlowPresentValue:
        curve = context.curves.discount_curve(cashflow.amount.currency)
        discount = curve.discount(cashflow.payment_date)
        currency = cashflow.amount.currency if result_currency is None else result_currency
        value = product(money_value(cashflow.amount), discount, conversion)
        return CashFlowPresentValue(
            cashflow.payment_date,
            cashflow.amount,
            discount,
            conversion,
            priced_money(value, currency),
            curve.curve_id,
            origin,
            coupon_rate,
        )

    def _coupon(
        self, coupon: FixedRateCashFlow | FloatingRateCashFlow, context: PricingContext
    ) -> CashFlowPresentValue:
        accrual = positive_accrual(coupon.period.start, coupon.period.end, coupon.day_count)
        if isinstance(coupon, FixedRateCashFlow):
            rate, origin = coupon.rate, RateOrigin.FIXED_COUPON
        else:
            if coupon.fixing_date <= context.snapshot.valuation_date:
                index_rate = context.snapshot.fixing(
                    coupon.notional.currency, coupon.index, coupon.fixing_date
                ).rate
                origin = RateOrigin.HISTORICAL_FIXING
            else:
                index_rate = context.curves.forward_curve(
                    coupon.notional.currency, coupon.index
                ).simple_rate(coupon.period.start, coupon.period.end, coupon.day_count)
                origin = RateOrigin.PROJECTED_FIXING
            rate = total((product(coupon.gearing, index_rate), coupon.spread))
        amount = priced_money(
            product(money_value(coupon.notional), rate, accrual), coupon.notional.currency
        )
        return self._payment(
            CashFlow(coupon.period.payment_date, amount), context, origin, coupon_rate=rate
        )

    def price(self, instrument: Instrument, context: PricingContext) -> PricingResult:
        """Price signed future cash flows and return auditable NPV contributions.

        Bonds are long/default-free; swaps contain coupon legs only; FX forwards
        report in quote currency. Paid flows are excluded. No historical fixing,
        projection curve, FX orientation or financial convention is inferred.
        """
        if not isinstance(context, PricingContext):
            raise PricingError("Pricing requires an explicit PricingContext")
        flows: list[CashFlowPresentValue] = []
        assumptions = [
            "Receivables positive; payables negative; amounts are currency units.",
            "Deterministic binary64 pricing; Decimal inputs converted explicitly; "
            "no settlement rounding.",
            "Payment dates/schedules supplied by caller; no calendar adjustment inferred.",
            "Valuation-date payments included."
            if context.include_valuation_date_payments
            else "Valuation-date and earlier payments excluded.",
        ]
        if isinstance(instrument, CashFlow):
            currency = instrument.amount.currency
            if context.includes_payment(instrument.payment_date):
                flows.append(self._payment(instrument, context, RateOrigin.KNOWN_PAYMENT))
        elif isinstance(instrument, (FixedRateCashFlow, FloatingRateCashFlow)):
            currency = instrument.notional.currency
            if context.includes_payment(instrument.period.payment_date):
                flows.append(self._coupon(instrument, context))
        elif isinstance(instrument, ZeroCouponBond):
            currency = instrument.face_value.currency
            assumptions.append(
                "Default-free long zero-coupon bond; no issuance or funding cash flow."
            )
            if context.includes_payment(instrument.maturity):
                flows.append(
                    self._payment(
                        CashFlow(instrument.maturity, instrument.face_value),
                        context,
                        RateOrigin.REDEMPTION,
                    )
                )
        elif isinstance(instrument, FixedRateBond):
            currency = instrument.face_value.currency
            assumptions.append(
                "Default-free long bond; NPV is dirty PV, not settlement clean price; "
                "no ex-coupon rules."
            )
            for period in instrument.periods:
                if context.includes_payment(period.payment_date):
                    flows.append(
                        self._coupon(
                            FixedRateCashFlow(
                                instrument.face_value,
                                instrument.coupon_rate,
                                period,
                                instrument.day_count,
                            ),
                            context,
                        )
                    )
            redemption = CashFlow(instrument.periods[-1].payment_date, instrument.face_value)
            if context.includes_payment(redemption.payment_date):
                flows.append(self._payment(redemption, context, RateOrigin.REDEMPTION))
        elif isinstance(instrument, InterestRateSwap):
            currency = instrument.notional.currency
            assumptions.append(
                "Vanilla single-currency fixed/simple-index swap; "
                "no principal exchanges or convexity adjustments."
            )
            fixed_notional = (
                -instrument.notional
                if instrument.direction == SwapDirection.PAY_FIXED
                else instrument.notional
            )
            floating_notional = -fixed_notional
            for period in instrument.fixed_periods:
                if context.includes_payment(period.payment_date):
                    flows.append(
                        self._coupon(
                            FixedRateCashFlow(
                                fixed_notional,
                                instrument.fixed_rate,
                                period,
                                instrument.fixed_day_count,
                            ),
                            context,
                        )
                    )
            for period, fixing in zip(
                instrument.floating_periods, instrument.fixing_dates, strict=True
            ):
                if context.includes_payment(period.payment_date):
                    flows.append(
                        self._coupon(
                            FloatingRateCashFlow(
                                floating_notional,
                                period,
                                fixing,
                                instrument.index,
                                instrument.floating_day_count,
                                instrument.floating_spread,
                                instrument.floating_gearing,
                            ),
                            context,
                        )
                    )
        elif isinstance(instrument, FxForward):
            currency = instrument.quote_currency
            assumptions.append(
                "Deliverable FX forward in QUOTE currency; spot is QUOTE/BASE "
                "with explicit value date; no cross-currency basis."
            )
            if context.includes_payment(instrument.maturity):
                spot = context.snapshot.fx_spot(instrument.base_notional.currency, currency)
                if instrument.maturity < spot.value_date:
                    raise PricingError("FX forward maturity cannot precede quoted spot value date")
                base_amount = (
                    instrument.base_notional
                    if instrument.direction == FxDirection.BUY_BASE
                    else -instrument.base_notional
                )
                quote_amount = Money(base_amount.amount.copy_negate(), currency).scale(
                    instrument.strike
                )
                flows.append(
                    self._payment(
                        CashFlow(instrument.maturity, base_amount),
                        context,
                        RateOrigin.FX_PAYMENT,
                        result_currency=currency,
                        conversion=_fx_conversion(spot, context),
                    )
                )
                flows.append(
                    self._payment(
                        CashFlow(instrument.maturity, quote_amount), context, RateOrigin.FX_PAYMENT
                    )
                )
        else:
            raise PricingError(
                "Instrument is not supported by the deterministic discounting engine"
            )
        if currency not in context.snapshot.currencies:
            raise PricingError("Instrument reporting currency is absent from market snapshot")
        assumptions.extend(
            f"Discount {curve.currency}: {curve.curve_id}, {curve.day_count}, "
            f"{curve.interpolation}, {curve.extrapolation}."
            for curve in context.curves.discount_curves
        )
        assumptions.extend(
            f"Projection {forward.curve.currency}/{forward.index}: {forward.curve.curve_id}."
            for forward in context.curves.forward_curves
        )
        ordered = tuple(sorted(flows, key=lambda item: item.payment_date))
        return PricingResult(
            priced_money(
                total(tuple(money_value(item.present_value) for item in ordered)), currency
            ),
            context.snapshot.valuation_date,
            "deterministic-discounting",
            ModelVersion("0.2.0"),
            tuple(assumptions),
            ordered,
            context.snapshot.snapshot_hash,
            context.curves.curve_hash,
            content_hash(instrument),
        )
