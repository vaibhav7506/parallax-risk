# First-class deterministic pricing workflow

This workflow is available through the Python domain/application library and the
synthetic demo, not a financial HTTP endpoint or production pricing CLI command.

| Step | Financial meaning and exact code | Input/output and failure |
|---|---|---|
| Validate market | MarketSnapshotInput in application/market_data | JSON → frozen source-labelled snapshot; invalid types/dates/duplicates fail |
| Assign curves | CurveSet in domain/market/curves/term_structures | Explicit discount/projection representations → currency/index lookup; no missing fallback |
| Validate contract | CashFlow/bond/swap/FX classes in domain/instruments | Money, schedule, direction → validated obligations; inconsistent schedules/units fail |
| Correlate run | PricingService.price in application/pricing | Contract/context/RunContext → safe workflow events and injected valuation |
| Resolve payments | DiscountingEngine.price in domain/pricing/engine | Exclude settled flows; generate signed coupon/redemption/FX obligations |
| Resolve coupon | DiscountingEngine._coupon | Historical fixing or future projection → simple annual coupon; missing known fixing/index fails |
| Discount | DiscountingEngine._payment | Original Money + D/payment/FX conversion → reporting-currency CashFlowPresentValue; range/horizon errors fail |
| Reconcile evidence | PricingResult in domain/pricing/results | Compensated sum → NPV, currency/date/model/assumptions/input hashes and flow evidence |
| Bump/reprice | sensitivities.parallel_rate_sensitivity / fx_delta | Immutable up/down inputs → derivative and base/up/down evidence; invalid bumps fail |

For a USD future payment of 100 at discount D, PV is `100*D` USD; a payable is negative.
This explanatory formula is not an observed market result. Bond/swap/FX interpretation
and actual running example are in the [tutorial](../tutorials/01-FIRST-PRICING-RUN.md).
Use [methodology](../methodology/PRICING.md) for assumptions, precision and formulas.

The service logs event/outcome/run ID/error class, not raw amounts or connection strings.
`PricingRunResult` ties the result to the envelope; it is not persisted automatically.
