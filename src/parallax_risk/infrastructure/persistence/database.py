"""SQLAlchemy PostgreSQL adapter; no schema creation or import-time connections."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from parallax_risk.common.errors import ConfigurationError, InfrastructureError


class PostgresConnectivity:
    """Own a lazy SQLAlchemy engine; bound connection and query timeouts.

    No governance tables, migrations or repository implementations are created.
    """

    def __init__(self, url: str, *, timeout_seconds: int = 5) -> None:
        try:
            parsed = make_url(url)
        except SQLAlchemyError:
            raise ConfigurationError("Invalid PostgreSQL connection configuration") from None
        if parsed.drivername != "postgresql+psycopg":
            raise ConfigurationError("PostgreSQL with psycopg is required")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 30:
            raise ConfigurationError("Database timeout must be an integer from 1 to 30 seconds")
        self._engine: Engine = create_engine(
            parsed,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
            pool_timeout=timeout_seconds,
            hide_parameters=True,
            connect_args={
                "connect_timeout": timeout_seconds,
                "options": f"-c statement_timeout={timeout_seconds * 1000}",
            },
        )

    def check(self) -> None:
        """Execute a bounded SELECT 1; expose only a sanitized dependency error."""
        try:
            with self._engine.connect() as connection:
                if connection.execute(text("SELECT 1")).scalar_one() != 1:
                    raise InfrastructureError("PostgreSQL connectivity check returned invalid data")
        except SQLAlchemyError:
            raise InfrastructureError("PostgreSQL connectivity check failed") from None

    def close(self) -> None:
        """Dispose of connection pool on service shutdown."""
        self._engine.dispose()
