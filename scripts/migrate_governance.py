"""Explicit upgrade of the configured PostgreSQL governance schema; no automatic downgrade."""

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from parallax_risk.application.config import load_settings
from parallax_risk.common.errors import ConfigurationError
from parallax_risk.infrastructure.persistence.migrate import migrate


def main() -> None:
    settings = load_settings()
    if settings.database_url is None:
        raise ConfigurationError("Explicit PostgreSQL configuration is required")
    engine = create_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.database_connect_timeout_seconds,
            "options": "-c statement_timeout=30000",
        },
    )
    try:
        with engine.begin() as connection:
            migrate(connection)
    except SQLAlchemyError:
        raise ConfigurationError("Governance migration failed; database details withheld") from None
    finally:
        engine.dispose()
    print("Parallax Risk governance schema upgraded to Alembic revision 0011.")


if __name__ == "__main__":
    main()
