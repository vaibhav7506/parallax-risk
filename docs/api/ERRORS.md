# Errors and boundaries

Operational readiness exposes safe 503 states instead of underlying connection
strings/driver details. Unexpected service errors are not replaced by a fake healthy
response. Configuration validation happens at explicit factory/CLI invocation.

Library failures derive from `ParallaxError` in `src/parallax_risk/common/errors.py`:
DomainValidationError, ConventionError, CurrencyMismatchError, MarketDataError,
MissingMarketDataError, CurveError, CurveBootstrapError, PricingError, NumericalError,
ConfigurationError and InfrastructureError. NumericalError is an arithmetic failure,
not necessarily a DomainValidationError. PricingService logs safe error class and rethrows.

Pydantic ingestion reports boundary ValidationError. No general financial HTTP error
schema or mapping exists because no such endpoint exists. CLI config/check-db failures
print authored safe errors to stderr and return exit 1; argparse errors use its own
exit semantics. Do not infer quantitative error codes from operational responses.

Phase 4 library failures include SimulationError for sequence/grid/sampling-unit and
workflow contracts, plus existing model/correlation/numerical failures. They propagate
through the research service with safe outcome logging; there is no simulation HTTP
route that maps them to a new financial response schema.

Phase 5 library scope/lifecycle/CSA/ledger/pricer-evidence violations raise
DomainValidationError. Existing missing-market/numerical errors propagate. No
financial HTTP operation or new HTTP error mapping is implemented.
