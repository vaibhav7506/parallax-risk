"""Explicitly synthetic research inputs; shared fixtures call production configuration."""

import io
from datetime import UTC, datetime

from parallax_risk.application.config import Settings
from parallax_risk.application.context import create_run_context
from parallax_risk.application.simulation import SimulationService
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.simulation.contracts import (
    ProcessComponent,
    Scheme,
    SimulationRequest,
    TimeGrid,
)
from parallax_risk.domain.simulation.engine import MonteCarloEngine
from parallax_risk.domain.simulation.observables import TerminalObservable
from parallax_risk.domain.simulation.random import SequenceKind, SequenceSpec, StreamKey


def component(model=None, *, state=(100.0,), scheme=Scheme.EXACT, name="asset"):
    return ProcessComponent(
        name,
        GeometricBrownianMotion(0.05, 0.2) if model is None else model,
        state,
        scheme,
        tuple("explicit_research_state_units" for _ in state),
        "Q",
    )


def request(*, paths=4096, batch=512, kind=SequenceKind.PSEUDO, antithetic=False):
    return SimulationRequest(
        (component(),),
        TimeGrid((0.0, 0.25, 1.0)),
        paths,
        batch,
        SequenceSpec(StreamKey(20251001, 0, 0), kind, antithetic),
    )


def context(seed=20251001):
    return create_run_context(
        Settings(default_seed=seed),
        seed=seed,
        run_id=RiskRunId("phase4-test"),
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
    )


def service(engine=None):
    stream = io.StringIO()
    return SimulationService(
        MonteCarloEngine() if engine is None else engine,
        create_logger(stream=stream),
    ), stream


def terminal():
    return TerminalObservable("terminal_spot", "USD/unit", 0)
