"""Factory-based FastAPI composition; imports never start engines or load settings."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from starlette.concurrency import run_in_threadpool

from parallax_risk import __version__
from parallax_risk.api.schemas import HealthResponse, ReadinessResponse, VersionResponse
from parallax_risk.application.config import Settings, load_settings
from parallax_risk.application.ports import ConnectivityProbe
from parallax_risk.common.errors import InfrastructureError
from parallax_risk.common.logging import create_logger
from parallax_risk.infrastructure.persistence.database import PostgresConnectivity


def create_app(
    settings: Settings | None = None, *, connectivity: ConnectivityProbe | None = None
) -> FastAPI:
    """Compose operational endpoints and own dependency cleanup in lifespan.

    An injected probe is application-owned and is closed at shutdown.
    Database failures degrade /ready to 503; /health stays a liveness probe.
    """
    effective = load_settings() if settings is None else settings
    logger = create_logger(effective.log_level)
    probe = connectivity
    started = False

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal probe, started
        if probe is None and effective.database_url is not None:
            probe = PostgresConnectivity(
                effective.database_url.get_secret_value(),
                timeout_seconds=effective.database_connect_timeout_seconds,
            )
        started = True
        logger.event("service_started", outcome=effective.environment)
        try:
            yield
        finally:
            started = False
            if probe is not None:
                await run_in_threadpool(probe.close)
            logger.event("service_stopped", outcome="closed")

    app = FastAPI(title="Parallax Risk", version=__version__, lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/ready", response_model=ReadinessResponse, tags=["operations"])
    async def ready(response: Response) -> ReadinessResponse:
        if not started:
            response.status_code = 503
            return ReadinessResponse(status="not_ready", database="unavailable")
        if probe is None:
            response.status_code = 503
            return ReadinessResponse(status="not_ready", database="not_configured")
        try:
            await run_in_threadpool(probe.check)
        except InfrastructureError:
            response.status_code = 503
            logger.event(
                "dependency_check", outcome="unavailable", error_type="InfrastructureError"
            )
            return ReadinessResponse(status="not_ready", database="unavailable")
        return ReadinessResponse(status="ready", database="connected")

    @app.get("/version", response_model=VersionResponse, tags=["operations"])
    def version() -> VersionResponse:
        return VersionResponse(version=__version__)

    return app
