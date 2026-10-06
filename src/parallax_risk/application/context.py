"""Immutable run lineage envelope; identity and timestamp do not drive random draws."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from parallax_risk.application.config import MAX_SEED, Settings
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.time import utc_timestamp


@dataclass(frozen=True, slots=True)
class RunContext:
    """Run identity, UTC timestamp, uint64 seed and canonical config digest.

    A replay preserves these values explicitly. Phase 4 streams use seed and
    sequence metadata, never wall clock or run ID.
    """

    run_id: RiskRunId
    timestamp: datetime
    seed: int
    configuration_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RiskRunId):
            raise DomainValidationError("Run identity must be RiskRunId")
        object.__setattr__(self, "timestamp", utc_timestamp(self.timestamp))
        if type(self.seed) is not int or not 0 <= self.seed <= MAX_SEED:
            raise DomainValidationError("Seed must be an unsigned 64-bit integer")
        if not isinstance(self.configuration_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.configuration_hash
        ):
            raise DomainValidationError("Configuration hash must be a SHA-256 hex digest")

    def as_metadata(self) -> dict[str, str | int]:
        """Export a JSON-safe lineage envelope with explicit UTC timestamp."""
        return {
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat(),
            "seed": self.seed,
            "configuration_hash": self.configuration_hash,
        }


def create_run_context(
    settings: Settings,
    *,
    run_id: RiskRunId | None = None,
    timestamp: datetime | None = None,
    seed: int | None = None,
) -> RunContext:
    """Create a context; inject ID/time for byte-identical metadata replay."""
    return RunContext(
        run_id=run_id if run_id is not None else RiskRunId(str(uuid4())),
        timestamp=timestamp if timestamp is not None else datetime.now(UTC),
        seed=settings.default_seed if seed is None else seed,
        configuration_hash=settings.configuration_hash(),
    )
