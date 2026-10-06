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
follow [how to change the code](docs/CODEBASE_GUIDE.md). Model/calibration primitives
and Monte Carlo research are implemented; XVA/governance
extension points described in the roadmap are NOT IMPLEMENTED and must wait for
their authorized phase. Finish only one phase, clean its disposable Docker resources,
report code/documentation/testing changes and stop before awaiting `go`.
