"""Operational CLI; quantitative workflows are exposed in their delivery phase."""

import argparse
import json
import sys
from collections.abc import Sequence

from parallax_risk import __version__
from parallax_risk.application.config import load_settings
from parallax_risk.application.context import create_run_context
from parallax_risk.common.errors import ConfigurationError, InfrastructureError
from parallax_risk.common.logging import create_logger
from parallax_risk.infrastructure.persistence.database import PostgresConnectivity


def main(argv: Sequence[str] | None = None) -> int:
    """Run version, redacted config, run-context and database-check commands."""
    parser = argparse.ArgumentParser(prog="parallax-risk", description="Parallax Risk operations")
    parser.add_argument("--version", action="version", version=f"Parallax Risk {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="Print release metadata")
    commands.add_parser("config", help="Validate and print redacted effective configuration")
    commands.add_parser("run-context", help="Create a reproducibility metadata envelope")
    commands.add_parser("check-db", help="Check configured PostgreSQL connectivity")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(json.dumps({"name": "Parallax Risk", "version": __version__, "phase": 2}))
        return 0
    try:
        settings = load_settings()
        if args.command == "config":
            print(json.dumps(settings.public_configuration(), sort_keys=True))
        elif args.command == "run-context":
            context = create_run_context(settings)
            create_logger(settings.log_level, stream=sys.stderr).event(
                "run_context_created", run_id=str(context.run_id), outcome="created"
            )
            print(json.dumps(context.as_metadata(), sort_keys=True))
        else:
            if settings.database_url is None:
                raise ConfigurationError("PostgreSQL is not configured")
            probe = PostgresConnectivity(
                settings.database_url.get_secret_value(),
                timeout_seconds=settings.database_connect_timeout_seconds,
            )
            try:
                probe.check()
            finally:
                probe.close()
            print(json.dumps({"database": "connected"}))
    except (ConfigurationError, InfrastructureError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0
