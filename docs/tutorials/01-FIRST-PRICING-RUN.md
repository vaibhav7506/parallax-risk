# Your first deterministic pricing run

## What you are learning
The demo prices a default-free zero-coupon bond, fixed-rate bond, pay-fixed swap and
buy-base FX forward. It also builds a deposit/par-swap curve and computes local rate/
FX sensitivities. Every observation and quote is a labelled synthetic teaching input.

## Inputs and reason for each
`data/sample/phase2_market.json` declares a 2025-01-01 valuation date, USD/EUR annual
zero rates with explicit day count/compounding, a direct EUR/USD spot with value date,
a known USD fixing and source/sample metadata. Curves discount future payments;
the fixing records what is already known; spot settlement matters for FX parity.
Volatility/credit observations are stored but no option/credit model consumes them.

The example supplies the actual contract notionals, coupon schedule/day counts and
directions in `scripts/demo_deterministic.py`. It calls production classes rather
than reimplementing valuation formulas.

## Run and inspect

Install/activate the [project environment](../../DEVELOPMENT.md), then:

```sh
python scripts/demo_deterministic.py
```

JSON stdout contains project/phase, explicit SYNTHETIC SAMPLE status, fixed run
metadata, snapshot/curve hashes, four detailed prices, bootstrap diagnostics,
bond_pv01/bond_dv01, fx_delta_per_spot_unit and fx_par_strike. Safe workflow logs
appear on stderr. No database or API call is needed for this calculation.

For each price inspect `npv` amount/currency, valuation_date, model_name/version,
assumptions and cashflows. Positive amounts are receivable; negative are payable.
Cash-flow PV contributions reconcile to NPV. The zero bond is one future redemption;
the fixed bond is dirty PV; the swap exchanges coupons only; the FX forward reports
in USD quote currency. DV01 is the negative of signed upward-rate PV01 by this
project's declared convention. FX delta is per one EUR/USD rate unit, not one percent.

Run it twice and compare stdout: fixed run fields and immutable inputs give repeatable
results. Log timestamps differ. `tests/integration/test_deterministic_workflow.py`
does this replay; `tests/quantitative/test_deterministic_pricing.py` independently
checks formulas/parity/sensitivity. The script also includes separate synthetic
bootstrap quotes; those quotes are not a vendor-calibrated market curve.

## Limits
Binary64 valuation, unrounded Decimal reporting, caller-supplied schedules, no
default/optionality/basis/stochastic paths. Read [pricing methodology](../methodology/PRICING.md),
[full conventions](../methodology/deterministic-pricing.md) and
[limitations](../LIMITATIONS.md) before extending the example.
