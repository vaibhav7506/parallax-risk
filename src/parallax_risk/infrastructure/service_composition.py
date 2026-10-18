"""Explicit composition of production engines and borrowed PostgreSQL resources."""

from sqlalchemy.engine import Engine

from parallax_risk.application.calibration import CalibrationService
from parallax_risk.application.ccr import CcrService
from parallax_risk.application.exposure import ExposureService
from parallax_risk.application.governance import Governance
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.service import RiskService
from parallax_risk.application.simulation import SimulationService
from parallax_risk.application.workflows import Workflows
from parallax_risk.application.xva import AdditiveXvaCalculator, XvaService
from parallax_risk.application.xva_revaluation import XvaRevaluation
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.domain.pricing.engine import DiscountingEngine
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from parallax_risk.infrastructure.persistence.governance import PostgresGovernance
from parallax_risk.infrastructure.persistence.service import PostgresJobs, PostgresObjects
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution


def make_workflows(logger: WorkflowLogger) -> Workflows:
    pricing, simulation = DiscountingEngine(), MonteCarloEngine()
    portfolio = PortfolioService(pricing, logger)
    exposure = ExposureService(simulation, portfolio, logger)
    return Workflows(
        pricing,
        portfolio,
        CalibrationService(ScipyLeastSquares(), logger),
        SimulationService(simulation, logger),
        exposure,
        XvaRevaluation(exposure, XvaService(AdditiveXvaCalculator(), logger)),
        CcrService(exposure),
        ScipyDifferentialEvolution(),
    )


def make_service(engine: Engine, logger: WorkflowLogger, maximum_pending: int = 64) -> RiskService:
    return RiskService(
        make_workflows(logger),
        PostgresJobs(engine),
        PostgresObjects(engine),
        Governance(PostgresGovernance(engine)),
        maximum_pending,
    )
