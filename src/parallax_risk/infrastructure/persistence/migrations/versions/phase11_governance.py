"""Initial append-only governance schema. Revision 0011, base None."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    kinds = (
        "'model','version','finding','approval','limitation','lineage',"
        "'policy','evaluation','alert'"
    )
    op.create_table(
        "governance_heads",
        sa.Column("kind", sa.String(32), primary_key=True),
        sa.Column("entity_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.CheckConstraint("revision >= 1", name="head_positive_revision"),
        sa.CheckConstraint(f"kind IN ({kinds})", name="head_known_kind"),
    )
    op.create_table(
        "governance_events",
        sa.Column("kind", sa.String(32), primary_key=True),
        sa.Column("entity_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer, primary_key=True),
        sa.Column("document", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.CheckConstraint("revision >= 1", name="event_positive_revision"),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="event_hash_format"),
        sa.CheckConstraint(
            "length(btrim(actor)) > 0 AND length(btrim(reason)) > 0", name="event_audit_text"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(document::jsonb) = 'object' "
            "AND document::jsonb->>'kind' IS NOT NULL "
            "AND document::jsonb->>'schema' IS NOT NULL "
            "AND document::jsonb->>'kind' = kind "
            "AND document::jsonb->>'schema' = '1'",
            name="event_document_schema",
        ),
        sa.ForeignKeyConstraint(
            ["kind", "entity_id"], ["governance_heads.kind", "governance_heads.entity_id"]
        ),
    )
    op.create_foreign_key(
        "head_has_event",
        "governance_heads",
        "governance_events",
        ["kind", "entity_id", "revision"],
        ["kind", "entity_id", "revision"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute("""CREATE FUNCTION parallax_governance_immutable() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'governance events are append only'; END $$""")
    op.execute(
        "CREATE TRIGGER governance_event_immutable BEFORE UPDATE OR DELETE "
        "ON governance_events FOR EACH ROW EXECUTE FUNCTION parallax_governance_immutable()"
    )
    op.execute("""CREATE FUNCTION parallax_governance_head_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'INSERT' THEN
        IF NEW.revision <> 1 THEN RAISE EXCEPTION 'initial revision must be one'; END IF;
      ELSE
        IF NEW.kind <> OLD.kind OR NEW.entity_id <> OLD.entity_id
        OR NEW.revision <> OLD.revision + 1
        OR OLD.kind NOT IN ('model','finding','alert') THEN
          RAISE EXCEPTION 'immutable identity or invalid revision advancement';
        END IF;
      END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER governance_head_guard BEFORE INSERT OR UPDATE "
        "ON governance_heads FOR EACH ROW EXECUTE FUNCTION parallax_governance_head_guard()"
    )


def downgrade() -> None:
    op.drop_constraint("head_has_event", "governance_heads", type_="foreignkey")
    op.drop_table("governance_events")
    op.drop_table("governance_heads")
    op.execute("DROP FUNCTION parallax_governance_immutable()")
    op.execute("DROP FUNCTION parallax_governance_head_guard()")
