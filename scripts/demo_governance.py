"""Generate seven HTML/JSON reports against an explicitly migrated PostgreSQL database."""

import argparse
from pathlib import Path

from sqlalchemy import create_engine

from parallax_risk.application.config import load_settings
from parallax_risk.application.governance import Governance
from parallax_risk.application.governance_examples import example
from parallax_risk.common.errors import ConfigurationError
from parallax_risk.infrastructure.calibration.scipy_solver import ScipyLeastSquares
from parallax_risk.infrastructure.persistence.governance import PostgresGovernance
from parallax_risk.infrastructure.validation.scipy_search import ScipyDifferentialEvolution


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallax Risk synthetic governance reports")
    parser.add_argument("--output", type=Path, default=Path("artifacts/local/phase11/reports"))
    args = parser.parse_args()
    settings = load_settings()
    if settings.database_url is None:
        raise ConfigurationError("Explicit migrated PostgreSQL configuration is required")
    engine = create_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.database_connect_timeout_seconds,
            "options": "-c statement_timeout=30000",
        },
    )
    try:
        reports = example(
            Governance(PostgresGovernance(engine)),
            ScipyLeastSquares(),
            ScipyDifferentialEvolution(),
        )
    finally:
        engine.dispose()
    args.output.mkdir(parents=True, exist_ok=True)
    for report in reports:
        (args.output / f"{report.kind.value}.json").write_text(report.json(), encoding="utf-8")
        (args.output / f"{report.kind.value}.html").write_text(report.html(), encoding="utf-8")
    print(f"Parallax Risk: {len(reports)} HTML/JSON report pairs at {args.output.resolve()}")


if __name__ == "__main__":
    main()
