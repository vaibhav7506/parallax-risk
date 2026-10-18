"""Durable service objects/jobs. Frozen revision 0012; extends unchanged 0011."""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE service_objects (
      owner varchar(128) NOT NULL, kind varchar(32) NOT NULL, key varchar(128) NOT NULL,
      document text NOT NULL, content_hash varchar(64) NOT NULL,
      created timestamptz NOT NULL, PRIMARY KEY(owner,kind,key),
      CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      CHECK(jsonb_typeof(document::jsonb) = 'object')
    )""")
    op.execute("""CREATE TABLE service_jobs (
      job_id varchar(128) PRIMARY KEY, owner varchar(128) NOT NULL,
      operation varchar(64) NOT NULL, idempotency_key varchar(128) NOT NULL,
      request text NOT NULL, request_hash varchar(64) NOT NULL,
      model_id varchar(128) NOT NULL, version_id varchar(128) NOT NULL,
      model_kind varchar(32) NOT NULL DEFAULT 'model' CHECK(model_kind='model'),
      version_kind varchar(32) NOT NULL DEFAULT 'version' CHECK(version_kind='version'),
      correlation_id varchar(128) NOT NULL, status varchar(16) NOT NULL,
      created timestamptz NOT NULL, updated timestamptz NOT NULL,
      result text, result_hash varchar(64), error_code varchar(64), claim varchar(128),
      lineage_kind varchar(32) NOT NULL DEFAULT 'lineage' CHECK(lineage_kind='lineage'),
      lineage_key varchar(128), UNIQUE(owner,idempotency_key),
      FOREIGN KEY(model_kind,model_id) REFERENCES governance_heads(kind,entity_id),
      FOREIGN KEY(version_kind,version_id) REFERENCES governance_heads(kind,entity_id),
      FOREIGN KEY(lineage_kind,lineage_key) REFERENCES governance_heads(kind,entity_id),
      CHECK(request_hash ~ '^[0-9a-f]{64}$'),
      CHECK(jsonb_typeof(request::jsonb)='object'),
      CHECK(updated >= created),
      CHECK(status IN ('queued','running','succeeded','failed')),
      CHECK((status='succeeded' AND result IS NOT NULL AND result_hash ~ '^[0-9a-f]{64}$'
         AND error_code IS NULL AND lineage_key IS NOT NULL AND lineage_key=job_id)
        OR (status='failed' AND result IS NULL AND result_hash IS NULL
         AND error_code IS NOT NULL AND lineage_key IS NULL)
        OR (status IN ('queued','running') AND result IS NULL AND result_hash IS NULL
         AND error_code IS NULL AND lineage_key IS NULL)),
      CHECK(status <> 'running' OR claim IS NOT NULL)
    )""")
    op.execute("CREATE INDEX service_jobs_queue ON service_jobs(status,created,job_id)")
    op.execute("CREATE INDEX service_jobs_owner ON service_jobs(owner,job_id)")
    op.execute("""CREATE TRIGGER service_object_immutable BEFORE UPDATE OR DELETE
      ON service_objects FOR EACH ROW EXECUTE FUNCTION parallax_governance_immutable()""")
    op.execute("""CREATE FUNCTION parallax_job_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$ BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status <> 'queued' OR NEW.claim IS NOT NULL THEN
          RAISE EXCEPTION 'initial job must be queued'; END IF;
      ELSE
        IF ROW(NEW.job_id,NEW.owner,NEW.operation,NEW.idempotency_key,NEW.request,
          NEW.request_hash,NEW.model_id,NEW.version_id,NEW.correlation_id,NEW.created,
          NEW.model_kind,NEW.version_kind,NEW.lineage_kind)
          IS DISTINCT FROM ROW(OLD.job_id,OLD.owner,OLD.operation,OLD.idempotency_key,
          OLD.request,OLD.request_hash,OLD.model_id,OLD.version_id,OLD.correlation_id,
          OLD.created,OLD.model_kind,OLD.version_kind,OLD.lineage_kind)
          OR NEW.updated < OLD.updated
          OR NOT ((OLD.status='queued' AND NEW.status IN ('running','failed'))
            OR (OLD.status='running' AND NEW.status IN ('succeeded','failed'))) THEN
          RAISE EXCEPTION 'immutable job inputs or invalid state transition'; END IF;
      END IF; RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER service_job_guard BEFORE INSERT OR UPDATE ON "
        "service_jobs FOR EACH ROW EXECUTE FUNCTION parallax_job_guard()"
    )
    op.execute(
        "CREATE TRIGGER service_job_no_delete BEFORE DELETE ON service_jobs "
        "FOR EACH ROW EXECUTE FUNCTION parallax_governance_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE service_jobs")
    op.execute("DROP TABLE service_objects")
    op.execute("DROP FUNCTION parallax_job_guard()")
