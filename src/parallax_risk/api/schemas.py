"""Pydantic response validation at the HTTP boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Process liveness; independent of database availability."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    """Declared dependency readiness; omitted database never implies persistence works."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["ready", "not_ready"]
    database: Literal["connected", "unavailable", "not_configured"]


class VersionResponse(BaseModel):
    """Release identity and current implementation phase."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: Literal["Parallax Risk"] = "Parallax Risk"
    version: str
    phase: Literal[4] = 4
