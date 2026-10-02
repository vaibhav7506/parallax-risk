"""Instance-local structured logging without global logging configuration."""

import logging
import sys
from dataclasses import dataclass
from typing import TextIO, cast

import structlog
from structlog.typing import FilteringBoundLogger

from parallax_risk.common.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class WorkflowLogger:
    """Restricted log envelope: portfolio values, credentials and URLs have no field."""

    _logger: FilteringBoundLogger

    def event(
        self,
        name: str,
        *,
        run_id: str | None = None,
        outcome: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """Emit a JSON workflow event with optional run correlation and safe status."""
        self._logger.info(name, run_id=run_id, outcome=outcome, error_type=error_type)


def create_logger(level: str = "INFO", *, stream: TextIO | None = None) -> WorkflowLogger:
    """Create an independent logger; no global structlog/logging mutation."""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    if level not in levels:
        raise ConfigurationError("Unsupported structured log level")
    logger = structlog.wrap_logger(
        structlog.PrintLogger(file=sys.stdout if stream is None else stream),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(levels[level]),
        cache_logger_on_first_use=True,
    )
    return WorkflowLogger(cast(FilteringBoundLogger, logger))
