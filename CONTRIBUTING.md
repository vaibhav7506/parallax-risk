# Contributing to Parallax Risk

Read [AGENTS](AGENTS.md), the [code guide](docs/CODEBASE_GUIDE.md) and the
[decision register](docs/decisions/README.md) first. Work in a `codex/` branch by
default unless the user specifies another name. Do not create/push commits or PRs
merely to update a phase count; record real implementation and evidence.

Use strict typed core Python, immutable domain inputs, explicit dependency injection,
focused functions and safe errors. Keep numeric/model logic out of HTTP/ORM code.
Never infer missing financial conventions, clip invalid values or invent benchmarks.

For quantitative changes, acceptance needs the mathematical specification and
plain-language intuition, units/signs/conventions, an implementation, an independent
benchmark, meaningful edge/property/regression tests, deliberate tolerances,
assumptions/limitations and implementation links. Update methodology, glossary and
phase evidence with actual results. Security/service changes also need operational
behavior and failure handling documented.

Run the [development checks](DEVELOPMENT.md). Review all canonical ADRs after every
phase, append history rows even if unchanged, update the decision ledger/changelog
and validate links. Supersede a decision with a new ID rather than rewriting history.

Current derivative extensions belong in implemented instrument/pricing modules;
follow [how to change the code](docs/CODEBASE_GUIDE.md). Model/calibration primitives,
Monte Carlo, exposure and XVA research are implemented; governance
extension points described in the roadmap are NOT IMPLEMENTED and must wait for
their authorized phase. Finish only one phase, clean its disposable Docker resources,
report code/documentation/testing changes and stop before awaiting `go`.

For Phase 5 portfolio changes, preserve legal boundaries, end-of-day lifecycle and
settled/pending distinction. Read [portfolio conventions](docs/methodology/PORTFOLIO_COLLATERAL.md)
and update independent checks plus all canonical ADR phase histories.

For Phase 6, preserve current-state conditional curves, retained known fixings,
legal-scope separation, independent random addresses and explicitly restricted
cash settlement. Quantile monotonicity is in confidence level, not arbitrary time.
Document survival-marginal changes and right-grid EAD bias/default-freeze omission.
See [exposure methodology](docs/methodology/EXPOSURE.md). Phase 7 extends those inputs into explicit unilateral/additive adjustments.

For Phase 7, preserve explicit unilateral credit and additive funding/IM assumptions,
component signs and reconciliation, admissible factor transformations, fixed sequence
addresses, actual h/h2 evidence and attribution residuals. Do not infer an IM model,
replace custom policies or project correlations silently. [XVA](docs/methodology/XVA.md).

For Phase 8, preserve restricted supported products, legal-unit isolation,
explicit business-day MPOR/NICA and the separate calendar CSA contract. Distinguish
standardized formula PFE from empirical quantile PFE, and illustrative capital
inputs from regulatory capital. Exception flags are not Findings. Keep component
bridge residuals and exact horizon-node rejection. See
[CCR methodology](docs/methodology/STANDARDIZED_CCR.md).
