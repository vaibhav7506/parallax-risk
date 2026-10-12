# Additive funding and external initial-margin cost

Phase 7 chooses a transparent deterministic spread/profile approximation. Positive
residual exposure is a borrowing proxy; negative residual magnitude is a lending
proxy. These are declared assumptions, not a reconstructed bank hedge/cash ledger.
Funding spreads are annual decimals **in excess of the discount/collateral
remuneration benchmark**. They are nonnegative and piecewise constant on [a,b),
with no extrapolation. At the last endpoint the final interval spread is returned.

```text
FCA = integral D(t) s_borrow(t) EE(t) dt >= 0
FBA = integral D(t) s_lend(t) ENE(t) dt >= 0, if explicitly enabled; otherwise 0
FVA adjustment = -FCA + FBA
MVA adjustment = -integral D(t) s_IM(t) expected_posted_IM(t) dt <= 0
```

All amounts use reporting-currency units; time is ACT/365F years. FundingTerms'
explicit boolean controls inclusion of the lending benefit. Lending inputs remain
validated even when benefit is disabled. FVA can be a cost or benefit.

## Margin ownership and quadrature

`MarginProfile` supplies externally estimated **expected segregated posted IM**,
with currency, exact exposure grid, nonnegative finite amounts and source description.
This is separate from the reusable signed CSA independent amount in Phase 5. No
regulatory/SIMM/VaR estimator, custody process, IM cash settlement or recalibration is
inferred. A zero profile explicitly represents no IM cost. Posted IM is excluded
from the FCA borrowing proxy and charged once in MVA.

Funding and margin use the union of amount, discount and spread knots. Amounts are
linearly interpolated. Each constant-spread interval uses
`spread(a) * (b-a) * [D(a)amount(a)+D(b)amount(b)]/2`.
FCA/FBA share one union grid to align their contributions. The rule is exact for
linear amounts at zero discount rate; otherwise it is a refinement-dependent
discounted quadrature approximation. All three spread horizons must cover the
profile. Negative spreads/amounts, missing inputs and nonfinite arithmetic fail.

## Financial limitations

This formulation has no survival/default termination in funding or margin costs,
recursive dependence of funding needs on the adjusted price, hedge financing,
reusable/excess-collateral funding flows or asymmetric institution-wide treasury
aggregation. Discounting is deterministic. Borrowing/lending spreads may contain
credit risk in practice; summing CVA/DVA and FVA does not automatically avoid economic
double counting. The caller must justify benchmark/spread/profile choices. No
replication, arbitrage consistency or production calibration approval is claimed.

Funding curves and external IM stay fixed during the implemented market/credit/CSA
bumps. MVA therefore has zero derivatives with respect to these factors unless the
caller supplies a different endpoint profile for movement attribution. That is a
conditional sensitivity, not an assertion that economic IM is insensitive.

The motivation for retaining these limitations follows
[Pallavicini, Perini and Brigo's funding framework](https://arxiv.org/abs/1112.1521),
which treats funding valuation as a more involved pricing problem. This code does
not implement that framework. [Green and Kenyon's MVA research](https://arxiv.org/abs/1405.0508)
describes initial-margin funding within a richer replication/estimation approach;
the external expected-profile integral here is a chosen approximation.

## Implementation and verification

`src/parallax_risk/domain/xva/contracts.py`,
`src/parallax_risk/domain/xva/calculators.py`, `tests/quantitative/test_xva.py`.
Hand examples check FCA=2, FBA=0.5, FVA=-1.5 and MVA=-0.4 USD over two years
with the documented constant profiles/spreads. Tests check benefit opt-out,
piecewise spread knots, linear IM and independence of FCA from IM. The reported
results are calculations on synthetic inputs, not observed market benchmarks.

[Credit/result contract](XVA.md), [workflow](../workflows/XVA_WORKFLOW.md),
[ADR 0018](../decisions/0018-additive-funding-and-external-margin.md).
