import hashlib
import io
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from parallax_risk.application.config import Settings, load_settings
from parallax_risk.application.context import RunContext, create_run_context
from parallax_risk.common.errors import ConfigurationError, ConventionError, DomainValidationError
from parallax_risk.common.identifiers import RiskRunId
from parallax_risk.common.logging import create_logger


def test_config_defaults_validated_and_immutable():
    settings = Settings()
    assert settings.default_seed == 0
    assert settings.environment == "development"
    assert settings.tolerances.to_domain().is_close(1, 1 + 1e-10)
    with pytest.raises(ValidationError):
        settings.default_seed = 1
    with pytest.raises(ValidationError):
        settings.tolerances.absolute = 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_seed": -1},
        {"default_seed": 2**64},
        {"default_seed": True},
        {"default_seed": 1.0},
        {"default_seed": "1.0"},
        {"database_connect_timeout_seconds": 0},
        {"database_connect_timeout_seconds": True},
        {"database_connect_timeout_seconds": 31},
        {"environment": "invalid"},
        {"log_level": "TRACE"},
        {"unknown": 1},
        {"environment": "production"},
        {"tolerances": {"absolute": float("nan")}},
        {"tolerances": {"absolute": True}},
        {"tolerances": {"relative": 1}},
        {"tolerances": {"absolute": 0, "relative": 0}},
        {"tolerances": {"unknown": 1}},
    ],
)
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValidationError):
        Settings(**kwargs)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "sqlite:///x",
        "postgresql://u:p@localhost/x",
        "postgresql+psycopg://u:p@/x",
        "postgresql+psycopg://localhost/x",
        "postgresql+psycopg://u:p@localhost",
        "postgresql+psycopg://u:p@localhost:bad/x",
        "postgresql+psycopg://u:p@localhost:0/x",
        "postgresql+psycopg://u:p@localhost/x?q=bad",
        "postgresql+psycopg://u:p@localhost/x#f",
        "postgresql+psycopg://u:p@[bad/x",
    ],
)
def test_database_config_rejects_invalid_urls_without_exposing_secrets(url):
    with pytest.raises(ValidationError) as captured:
        Settings(database_url=url)
    assert url not in str(captured.value) if url else True


def test_environment_load_nested_overrides_and_sanitized_errors(monkeypatch):
    monkeypatch.setenv("PARALLAX_DEFAULT_SEED", "42")
    monkeypatch.setenv("PARALLAX_TOLERANCES__ABSOLUTE", "0.000001")
    monkeypatch.setenv("PARALLAX_ENVIRONMENT", "test")
    settings = load_settings()
    assert settings.default_seed == 42
    assert settings.tolerances.absolute == 1e-6
    assert settings.environment == "test"
    monkeypatch.setenv("PARALLAX_DATABASE_URL", "SECRET_INVALID_URL")
    with pytest.raises(ConfigurationError, match="Invalid Parallax Risk configuration") as error:
        load_settings()
    assert "SECRET_INVALID_URL" not in str(error.value)
    monkeypatch.delenv("PARALLAX_DATABASE_URL")
    monkeypatch.setenv("PARALLAX_TOLERANCES", "malformed-json-SECRET")
    with pytest.raises(ConfigurationError) as error:
        load_settings()
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize("name", ["PARALLAX_DEAFULT_SEED", "PARALLAX_DEFAULT_SEED__BAD"])
def test_unknown_environment_configuration_rejected(monkeypatch, name):
    monkeypatch.setenv(name, "secret-untrusted")
    with pytest.raises(ConfigurationError, match="Unknown") as error:
        load_settings()
    assert "secret" not in str(error.value)


def test_explicit_config_precedence_and_hash_semantics(monkeypatch):
    monkeypatch.setenv("PARALLAX_DEFAULT_SEED", "7")
    a = Settings(default_seed=3, database_url="postgresql+psycopg://u:secret-a@localhost/db")
    b = Settings(database_url="postgresql+psycopg://u:secret-b@localhost/db", default_seed=3)
    assert a.configuration_hash() == b.configuration_hash()
    assert (
        a.configuration_hash()
        != Settings(default_seed=4, database_url=b.database_url).configuration_hash()
    )
    assert a.configuration_hash() != Settings(default_seed=3).configuration_hash()
    encoded = json.dumps(
        {"schema_version": 1, "settings": a.public_configuration()},
        sort_keys=True,
        separators=(",", ":"),
    )
    assert a.configuration_hash() == hashlib.sha256(encoded.encode()).hexdigest()
    for export in (repr(a), str(a), json.dumps(a.public_configuration()), a.model_dump_json()):
        assert "secret-a" not in export
        assert "postgresql" not in export
    assert a.public_configuration()["database_configured"] is True
    assert (
        Settings(environment="production", database_url=b.database_url).environment == "production"
    )


def test_run_context_injection_and_default_creation():
    settings = Settings(default_seed=17)
    timestamp = datetime(2026, 9, 30, tzinfo=UTC)
    first = create_run_context(settings, run_id=RiskRunId("run-1"), timestamp=timestamp, seed=0)
    second = create_run_context(settings, run_id=RiskRunId("run-1"), timestamp=timestamp, seed=0)
    assert first == second
    assert first.as_metadata() == {
        "run_id": "run-1",
        "timestamp": timestamp.isoformat(),
        "seed": 0,
        "configuration_hash": settings.configuration_hash(),
    }
    default = create_run_context(settings)
    assert default.seed == 17
    assert default.timestamp.tzinfo is UTC
    assert default.run_id != create_run_context(settings).run_id
    with pytest.raises(FrozenInstanceError):
        first.seed = 3


@pytest.mark.parametrize(
    "override,error",
    [
        ({"run_id": "run-1"}, DomainValidationError),
        ({"seed": True}, DomainValidationError),
        ({"seed": -1}, DomainValidationError),
        ({"seed": 2**64}, DomainValidationError),
        ({"configuration_hash": "x" * 64}, DomainValidationError),
        ({"configuration_hash": 1}, DomainValidationError),
        ({"timestamp": datetime(2026, 1, 1)}, ConventionError),
    ],
)
def test_run_context_rejects_invalid_metadata(override, error):
    values = {
        "run_id": RiskRunId("x"),
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "seed": 1,
        "configuration_hash": "a" * 64,
    }
    values.update(override)
    with pytest.raises(error):
        RunContext(**values)


def test_instance_logging_json_correlation_and_level_isolation():
    stream, quiet = io.StringIO(), io.StringIO()
    logger = create_logger("INFO", stream=stream)
    other = create_logger("ERROR", stream=quiet)
    other.event("suppressed", outcome="test")
    logger.event("run_created", run_id="run-1", outcome="created")
    value = json.loads(stream.getvalue())
    assert value["event"] == "run_created"
    assert value["run_id"] == "run-1"
    assert value["level"] == "info"
    assert value["timestamp"].endswith("Z")
    assert set(value) == {"event", "run_id", "outcome", "error_type", "level", "timestamp"}
    assert quiet.getvalue() == ""
    with pytest.raises(ConfigurationError):
        create_logger("UNKNOWN")
