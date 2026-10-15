# First adversarial lab run

From the repository root after development installation:

```sh
python scripts/demo_adversarial.py
python -m pytest -q tests/quantitative/test_adversarial_lab.py tests/unit/test_adversarial_guards.py tests/integration/test_adversarial_workflow.py --no-cov
python scripts/check_docs.py
```

The JSON includes the actual synthetic probe and independent targets. Compare the
complete and sign-only suites: every miss remains in the evidence and denominator.
Do not generalize those rates to other inputs or full production models. The dated
calibration values are supplied synthetic observations, not retrieved historical fits.

Read the search specification before its best discrepancy: bounds, units, combined
constraint, source, stream and budget explain the experiment. Read converged/message
and actual evaluation count. A false convergence flag or best disagreement does not
invalidate the successful execution of the experiment or imply a market probability.

Read diagnostics.change, materiality, repeat_checks, possible cause fingerprints,
ordered steps and residual. A materiality failure is a trigger for investigation;
repeatability success is not proof of accuracy. The demo intentionally leaves a
portfolio exposure change unexplained by its rate/recovery bridge.

To extend the experiment, supply typed MutationModel/ProductionModel/ChallengerModel
adapters, independent check targets and actual immutable cases. For XVA, use
XvaCvaProduction, IndependentCreditCvaChallenger and XvaSearchCases with exact factor
units and a valid baseline, including a daily grid/accounts where a CSA is present.
Retain complete cases and selected model implementations alongside hashes and JSON.
No financial API, automatic approval, persisted governance or Phase 11 workflow exists.

Focused --no-cov is intentional; whole-release branch-inclusive coverage is verified
separately with live PostgreSQL and the installed Linux wheel. See
[workflow](../workflows/ADVERSARIAL_WORKFLOW.md), [methods](../methodology/ADVERSARIAL_SEARCH.md),
[actual results](../validation/phase-10.md).
