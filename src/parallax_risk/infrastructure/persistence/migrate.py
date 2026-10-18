"""Explicit, caller-owned Alembic migration composition; no engine or settings globals."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection


def migrate(
    connection: Connection,
    *,
    downgrade_to_base: bool = False,
    allow_destructive: bool = False,
    target_revision: str = "head",
) -> None:
    """Upgrade explicitly to head/0011/0012; destructive reversal requires opt-in.

    Caller owns the surrounding transaction/connection and database selection.
    Normal service startup never applies migrations.
    """
    if type(downgrade_to_base) is not bool or type(allow_destructive) is not bool:
        raise ValueError("Migration switches must be booleans")
    if connection.dialect.name != "postgresql":
        raise ValueError("Migrations require PostgreSQL")
    if target_revision not in ("head", "0011", "0012"):
        raise ValueError("Unsupported migration revision")
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.attributes["connection"] = connection
    if downgrade_to_base:
        if not allow_destructive:
            raise ValueError("Downgrade removes governance data; explicit opt-in is required")
        command.downgrade(config, "base")
    else:
        command.upgrade(config, target_revision)
