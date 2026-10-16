"""SQLAlchemy PostgreSQL snapshot/event repository with guarded compare-and-swap writes."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from parallax_risk.application.governance import ConflictError, Reference, Snapshot, validate_write
from parallax_risk.application.governance_codec import decode, encode, record_key
from parallax_risk.common.errors import DomainValidationError, InfrastructureError
from parallax_risk.domain._validation import require_token
from parallax_risk.domain.governance.contracts import Document

# Table descriptions are inert. Migration DDL is frozen separately, not create_all.
metadata = MetaData()
heads = Table(
    "governance_heads",
    metadata,
    Column("kind", String(32), primary_key=True),
    Column("entity_id", String(128), primary_key=True),
    Column("revision", Integer, nullable=False),
    CheckConstraint("revision >= 1", name="head_positive_revision"),
)
events = Table(
    "governance_events",
    metadata,
    Column("kind", String(32), primary_key=True),
    Column("entity_id", String(128), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("document", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("actor", Text, nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("reason", Text, nullable=False),
    ForeignKeyConstraint(
        ["kind", "entity_id"], ["governance_heads.kind", "governance_heads.entity_id"]
    ),
    CheckConstraint("revision >= 1", name="event_positive_revision"),
)


def _snapshot(row: Any) -> Snapshot:
    document = Document(row.document)
    if document.hash != row.content_hash:
        raise InfrastructureError("Governance evidence digest mismatch")
    record = decode(document)
    if record_key(record) != (row.kind, row.entity_id) or not isinstance(row.timestamp, datetime):
        raise InfrastructureError("Governance stored identity mismatch")
    return Snapshot(record, row.revision, row.actor, row.timestamp, row.reason)


class PostgresGovernance:
    """Borrow an explicitly owned PostgreSQL engine; never migrate on construction."""

    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise DomainValidationError("Governance persistence requires PostgreSQL")
        self.engine = engine

    def get(self, kind: str, entity_id: str) -> Snapshot | None:
        require_token(kind)
        require_token(entity_id)
        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    select(events)
                    .join(
                        heads,
                        (events.c.kind == heads.c.kind)
                        & (events.c.entity_id == heads.c.entity_id)
                        & (events.c.revision == heads.c.revision),
                    )
                    .where(events.c.kind == kind, events.c.entity_id == entity_id)
                ).first()
                return None if row is None else _snapshot(row)
        except SQLAlchemyError:
            raise InfrastructureError("Governance read failed") from None

    def history(self, kind: str, entity_id: str) -> tuple[Snapshot, ...]:
        require_token(kind)
        require_token(entity_id)
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(events)
                    .where(events.c.kind == kind, events.c.entity_id == entity_id)
                    .order_by(events.c.revision)
                )
                return tuple(_snapshot(row) for row in rows)
        except SQLAlchemyError:
            raise InfrastructureError("Governance history read failed") from None

    def save(
        self, snapshot: Snapshot, expected_revision: int, references: tuple[Reference, ...]
    ) -> None:
        validate_write(snapshot, expected_revision, references)
        kind, entity_id = record_key(snapshot.record)
        document = encode(snapshot.record)
        try:
            with self.engine.begin() as connection:
                # Ordered locks prevent opposite reference order from deadlocking.
                guards = references + (
                    (Reference(kind, entity_id, expected_revision),) if expected_revision else ()
                )
                for reference in sorted(guards, key=lambda value: (value.kind, value.entity_id)):
                    revision = connection.execute(
                        select(heads.c.revision)
                        .where(
                            heads.c.kind == reference.kind, heads.c.entity_id == reference.entity_id
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if revision != reference.revision:
                        raise ConflictError("Governance reference revision changed")
                if expected_revision == 0:
                    connection.execute(
                        insert(heads).values(kind=kind, entity_id=entity_id, revision=1)
                    )
                else:
                    result = connection.execute(
                        update(heads)
                        .where(
                            heads.c.kind == kind,
                            heads.c.entity_id == entity_id,
                            heads.c.revision == expected_revision,
                        )
                        .values(revision=snapshot.revision)
                    )
                    if result.rowcount != 1:
                        raise ConflictError("Governance revision changed")
                connection.execute(
                    insert(events).values(
                        kind=kind,
                        entity_id=entity_id,
                        revision=snapshot.revision,
                        document=document.text,
                        content_hash=document.hash,
                        actor=snapshot.actor,
                        timestamp=snapshot.timestamp,
                        reason=snapshot.reason,
                    )
                )
        except IntegrityError:
            raise ConflictError("Governance identifier or constraint conflict") from None
        except SQLAlchemyError:
            raise InfrastructureError("Governance transaction failed") from None
