# Vasicek risk-neutral short rates

## Purpose and intuition

A short rate returns towards a long-run rate, while Gaussian shocks can move it
above or below that level. Negative rates are possible. This model provides exact
conditional moments, transitions and default-free bond prices for numerical validation.

## Mathematics

Under the risk-neutral measure Q, `dr=a(theta-r)dt+sigma dW`, with a>0 in 1/year,
theta a decimal annual rate, and sigma in rate units/sqrt(year). For step h,
`E[r(t+h)|r]=theta+(r-theta)exp(-a h)` and
`Var[r(t+h)|r]=sigma²(1-exp(-2a h))/(2a)`.
The exact transition adds this standard deviation times a supplied standard normal.

Let `B(a,h)=(1-exp(-a h))/a`. The conditional integrated rate has mean
`r B(a,h)+theta(h-B(a,h))` and variance
`sigma²/a² [h-2B(a,h)+B(2a,h)]`. A unit-nominal bond is the exponential of
minus that mean plus half that variance. No market price of risk is inferred.

## Implementation and error policy

Vasicek in `src/parallax_risk/domain/models/rates.py` uses expm1 for B. For a*h<1e-3,
the integrated-variance loading uses the expansion
`h³[1/3-x/4+7x²/60-x³/24+31x⁴/2520-x⁵/320+127x⁶/181440]`, x=a*h.
O(x⁷) relative truncation avoids catastrophic subtraction near zero. Derived finite
squares/exponentials are checked; unrepresentable prices fail explicitly. a=0 is
unsupported and rejected, rather than silently becoming another model.

## Calibration and example

VasicekBondProblem in `src/parallax_risk/domain/calibration/problems.py` fits
a, theta and sigma to unit-nominal discount factors with fixed initial short rate.
It is a local Q-parameter fit, not estimation of real-world historical dynamics.
Synthetic sample truth is (.35, .055, .025) with initial rate .02 and ten maturities
from .25 to 20 years. Run `python scripts/demo_calibration.py`.

## Validation and limitations

`tests/quantitative/test_stochastic_models.py` compares bonds against independent
numerical integration of the Gaussian mean/kernel for a down to 1e-9.
`tests/quantitative/test_calibration.py` checks recovery, repeatability, alternative
initialization and deliberate quote perturbations. The formula is also consistent
with [QuantLib's Vasicek reference implementation](https://github.com/lballabio/QuantLib/blob/master/ql/models/shortrate/onefactormodels/vasicek.cpp).

Constant parameters and Gaussian rates cannot reproduce arbitrary yield curves or
volatility smiles. Curve-only parameter identification can be weak; optimizer success
does not establish identification. No default, credit spread or rate-floor rule exists.
