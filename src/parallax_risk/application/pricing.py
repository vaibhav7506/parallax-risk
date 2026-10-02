"""Run-correlated deterministic pricing orchestration, independent of API/persistence."""

from dataclasses import dataclass

from parallax_risk.application.context import RunContext
from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.domain.pricing.engine import DiscountingEngine, Instrument, PricingContext
from parallax_risk.domain.pricing.results import PricingResult


@dataclass(frozen=True, slots=True)
class PricingRunResult:
    """Deterministic result linked to the existing run/configuration envelope."""

    context: RunContext
    price: PricingResult


@dataclass(frozen=True, slots=True)
class PricingService:
    """Injected engine/logger; logs record workflow state without financial inputs."""

    engine: DiscountingEngine
    logger: WorkflowLogger

    def price(
        self, instrument: Instrument, market: PricingContext, run: RunContext
    ) -> PricingRunResult:
        """Price once, propagate errors, and correlate safe outcome logs by run ID."""
        self.logger.event("pricing_started", run_id=str(run.run_id), outcome="started")
        try:
            result = self.engine.price(instrument, market)
        except ParallaxError as error:
            self.logger.event(
                "pricing_failed",
                run_id=str(run.run_id),
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event("pricing_completed", run_id=str(run.run_id), outcome="completed")
        return PricingRunResult(run, result)
