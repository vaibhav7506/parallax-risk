"""Alembic entry point, executed only by its script loader with an injected connection."""

from alembic import context
from sqlalchemy.engine import Connection


def run() -> None:
    connection = context.config.attributes.get("connection")
    if not isinstance(connection, Connection) or connection.dialect.name != "postgresql":
        raise ValueError("An explicitly owned PostgreSQL connection is required")
    context.configure(connection=connection, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()


# Alembic's load_python_file assigns env_py. Normal package imports remain inert.
if __name__ == "env_py":
    run()
