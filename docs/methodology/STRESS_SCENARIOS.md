# Sourced and hypothetical stress scenarios

Phase 9 implements actual scenario revaluation in
`src/parallax_risk/application/validation_stress.py` using ProductionXvaModel and the
existing XvaRevaluation transformations. [Validation workflow](../workflows/VALIDATION_WORKFLOW.md),
[admissible XVA factors](XVA_SENSITIVITIES.md), [ADR 0025](../decisions/0025-sourced-stress-scenarios.md).

StressScenario retains name, typed hypothetical/historical/combined kind, ordered
FactorMove values, source, description and optional observed interval or parent hashes.
Rate, direct FX, declared model volatility, credit-triangle spread, recovery, Brownian
correlation and CSA receive threshold use absolute movements and their exact units.
Invalid transformed inputs reject; no clamp, unsupported process fallback or silent
correlation repair is applied. Scenario names and movement names are unique.

Hypothetical scenarios use explicit caller shocks. Combined scenarios concatenate
ordered parent moves, prefix movement names and retain parent hashes. Repeated shocks
to a factor are applied in order and can interact; no commutativity or additivity is
assumed. Intermediate moves must be admissible even if a later offset would cancel.
They are not adversarial searches or controlled model mutations.

The historical adapter accepts caller-sourced before/after parameter observations
with exact factor-unit labels and start<end civil dates. It computes after-before
absolute shocks and replays them on the baseline configuration. No history is fetched
or fabricated, no unit conversion is inferred and no historical probability is assigned.
Source labels are provenance supplied by the caller, not independently authenticated
market-data certification. Tests use explicitly synthetic dated adapter inputs and
must not be reported as observed historical market stresses. The demo is hypothetical.

StressResult retains scenario provenance, baseline/stressed outputs, signed component
and TOTAL movements and factor units. The workflow revalues the baseline once and
actually revalues every scenario, enforcing a caller evaluation budget. Funding,
external IM, fixings and owned market/default sequences stay fixed during the listed
moves, according to Phase 7 semantics. Results are conditional sensitivities, not a
complete crisis model, event likelihood, liquidity simulation or stress governance.
No persistence, approvals, alerts, backtesting or monitoring is added in Phase 9.

## Phase 10 applicability

Bounded search complements the existing sourced ordered stress workflow. Search factor coordinates are ordered absolute deltas with the same admissibility restrictions; an optimizer-produced scenario has no authenticated historical observation or event likelihood.

[Search methods](../methodology/ADVERSARIAL_SEARCH.md), [phase evidence](../validation/phase-10.md).
