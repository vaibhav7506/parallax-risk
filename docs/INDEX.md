# Parallax Risk documentation

**Current: Phases 1–9 complete; release 0.9.0. Phase 10 NOT IMPLEMENTED.**

Start with the learning path below. FACT describes actual code/evidence; IMPLEMENTATION
DECISION describes a chosen policy; ASSUMPTION states its applicability; LIMITATION
describes missing behavior. PLANNED/DEFERRED documents are never implementation claims.

After every phase, update the decision ledger and every ADR phase history, then affected
guides, roadmap/changelog and evidence. `python scripts/check_docs.py` checks local links,
concrete repository references, index reachability and completed-phase ADR reviews.
External URL availability and future model correctness are not claimed by this check.

## New to Parallax Risk

- [Parallax Risk](../README.md)
- [Parallax Risk roadmap](../ROADMAP.md)
- [Financial and engineering glossary](GLOSSARY.md)
- [Domain relationships and financial ownership](DOMAIN_MODEL.md)
- [Architecture overview](architecture/OVERVIEW.md)
- [Implemented and planned workflow](WORKFLOW.md)
- [Your first deterministic pricing run](tutorials/01-FIRST-PRICING-RUN.md)
- [Your first calibration run](tutorials/02-FIRST-CALIBRATION-RUN.md)
- [Your first simulation research run](tutorials/03-FIRST-SIMULATION-RUN.md)
- [Your first portfolio run](tutorials/04-FIRST-PORTFOLIO-RUN.md)

## Understand and change the code

- [Parallax Risk codebase guide](CODEBASE_GUIDE.md)
- [Parallax Risk contributor and agent rules](../AGENTS.md)
- [Developing Parallax Risk](../DEVELOPMENT.md)
- [Contributing to Parallax Risk](../CONTRIBUTING.md)
- [Reproducing pricing and calibration](REPRODUCIBILITY.md)
- [Current limitations](LIMITATIONS.md)

## Decisions and phase changes

- [Parallax Risk decision register](decisions/README.md)
- [Parallax Risk changelog](../CHANGELOG.md)
- [Parallax Risk — Phase 1 completion evidence](validation/phase-1.md)
- [Parallax Risk — Phase 2 completion evidence](validation/phase-2.md)
- [Parallax Risk — Phase 3 implementation and verification](validation/phase-3.md)
- [Parallax Risk — Phase 4 implementation and verification](validation/phase-4.md)
- [Parallax Risk — Phase 5 implementation and verification](validation/phase-5.md)
- [Documentation maintenance evidence](validation/documentation-maintenance.md)
- [Historical decision records](adr/README.md)

## Quantitative methodology and validation

- [Implemented quantitative methodology](methodology/INDEX.md)
- [Market data and snapshot identity](methodology/MARKET_DATA.md)
- [Curves and bootstrap](methodology/CURVES.md)
- [Deterministic pricing](methodology/PRICING.md)
- [Stochastic process and discretization contracts](methodology/STOCHASTIC_PROCESSES.md)
- [Vasicek rates](methodology/VASICEK.md)
- [Hull–White rates and bond options](methodology/HULL_WHITE.md)
- [Geometric Brownian motion](methodology/GBM.md)
- [Heston variance and European calls](methodology/HESTON.md)
- [Correlation validation and explicit repair](methodology/CORRELATION.md)
- [Bounded calibration and uncertainty](methodology/CALIBRATION.md)
- [Primitive conventions, assumptions and limitations](methodology/primitives.md)
- [Parallax Risk: deterministic curves and pricing](methodology/deterministic-pricing.md)
- [Development checks and model validation](validation/OVERVIEW.md)
- [Deterministic benchmarking](validation/BENCHMARKING.md)
- [Sensitivity definitions and checks](validation/SENSITIVITY.md)
- [Test strategy and evidence](testing/STRATEGY.md)
- [First-class deterministic pricing workflow](workflows/PRICING_WORKFLOW.md)
- [Calibration workflow](workflows/CALIBRATION_WORKFLOW.md)
- [Monte Carlo paths and sequences](methodology/MONTE_CARLO.md)
- [Monte Carlo statistics](methodology/MONTE_CARLO_STATISTICS.md)
- [Portfolios, netting and collateral](methodology/PORTFOLIO_COLLATERAL.md)
- [Portfolio workflow](workflows/PORTFOLIO_WORKFLOW.md)
- [Simulation workflow](workflows/SIMULATION_WORKFLOW.md)
- [Monte Carlo benchmark methodology](validation/MONTE_CARLO_BENCHMARKS.md)
- [Moments/replay notebook](../notebooks/01-monte-carlo-reproducibility.ipynb)
- [Variance/convergence notebook](../notebooks/02-variance-reduction-convergence.ipynb)

## Architecture and operation

- [Components and ownership](architecture/COMPONENTS.md)
- [Data and evidence flow](architecture/DATA_FLOW.md)
- [Dependency rules](architecture/DEPENDENCY_RULES.md)
- [Current deployment topology](architecture/DEPLOYMENT.md)
- [Parallax Risk foundation architecture](architecture/foundation.md)
- [Local setup](operations/LOCAL_SETUP.md)
- [Configuration](operations/CONFIGURATION.md)
- [PostgreSQL scope and lifecycle](operations/DATABASE.md)
- [Docker verification cleanup and retention](operations/DOCKER.md)
- [Logs and health](operations/OBSERVABILITY.md)
- [Troubleshooting](operations/TROUBLESHOOTING.md)
- [Release and evidence checklist](operations/RELEASE.md)
- [Operational API philosophy and scope](api/OVERVIEW.md)
- [Implemented endpoints](api/ENDPOINTS.md)
- [Errors and boundaries](api/ERRORS.md)
- [Operational examples](api/EXAMPLES.md)
- [Parallax Risk security scope](../SECURITY.md)

## Deferred detailed documents

Governance, mutation/adversarial and production scale tutorials remain deferred.
Monte Carlo research, sequence policy and measured local benchmarks are implemented
in Phase 4; no future financial workflow is scaffolded.
Create future methodology/model/testing/tutorial pages alongside actual code and evidence.

## Phase 6 exposure and credit research

- [First exposure run](tutorials/05-FIRST-EXPOSURE-RUN.md)
- [Exposure workflow](workflows/EXPOSURE_WORKFLOW.md)
- [Pathwise repricing, statistics, collateral and grid EAD](methodology/EXPOSURE.md)
- [Hazard, survival and default sampling](methodology/CREDIT_DEFAULT.md)
- [Independent, static and dynamic wrong-way risk](methodology/WRONG_WAY_RISK.md)
- [Phase 6 verification and file manifest](validation/phase-6.md)

## Phase 7 XVA and sensitivity research

- [First XVA run](tutorials/06-FIRST-XVA-RUN.md)
- [XVA workflow](workflows/XVA_WORKFLOW.md)
- [Unilateral credit and signed result contract](methodology/XVA.md)
- [Additive funding and external segregated margin](methodology/FUNDING_MARGIN.md)
- [Seven factor types and ordered attribution residuals](methodology/XVA_SENSITIVITIES.md)
- [Phase 7 verification and file manifest](validation/phase-7.md)

## Phase 8 CCR prototype and challenger research

- [First CCR comparison](tutorials/07-FIRST-CCR-COMPARISON.md)
- [CCR workflow](workflows/CCR_WORKFLOW.md)
- [Restricted standardized methodology](methodology/STANDARDIZED_CCR.md)
- [Actual legal-unit IMM challenger](methodology/IMM_CHALLENGER.md)
- [Capital inputs, component bridges and exceptions](methodology/CCR_COMPARISON.md)
- [Phase 8 verification and file manifest](validation/phase-8.md)

## Phase 9 model validation lab

- [First validation run](tutorials/08-FIRST-VALIDATION-RUN.md)
- [Validation workflow](workflows/VALIDATION_WORKFLOW.md)
- [Comparable models, findings and numerical checks](methodology/MODEL_VALIDATION.md)
- [Selected risk uncertainty](methodology/MODEL_UNCERTAINTY.md)
- [Sourced and hypothetical stress](methodology/STRESS_SCENARIOS.md)
- [Phase 9 verification and manifest](validation/phase-9.md)
