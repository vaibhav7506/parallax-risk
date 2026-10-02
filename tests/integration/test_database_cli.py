import json
import os
from contextlib import contextmanager

import pytest
from sqlalchemy.exc import OperationalError

from parallax_risk.cli.main import main
from parallax_risk.common.errors import ConfigurationError, InfrastructureError
from parallax_risk.infrastructure.persistence.database import PostgresConnectivity


class Engine:
    def __init__(self, *, failure=False, scalar=1):
        self.failure = failure
        self.scalar = scalar
        self.disposed = False

    @contextmanager
    def connect(self):
        if self.failure:
            raise OperationalError("SECRET-SQL", {}, Exception("SECRET-CREDENTIAL"))
        yield self

    def execute(self, statement):
        assert str(statement) == "SELECT 1"
        return self

    def scalar_one(self):
        return self.scalar

    def dispose(self):
        self.disposed = True


def test_postgres_adapter_uses_bounded_lazy_engine_and_sanitizes_failures(monkeypatch):
    engine = Engine()
    calls = []

    def factory(url, **kwargs):
        calls.append((url, kwargs))
        return engine

    monkeypatch.setattr("parallax_risk.infrastructure.persistence.database.create_engine", factory)
    probe = PostgresConnectivity("postgresql+psycopg://u:p@localhost/test", timeout_seconds=3)
    assert len(calls) == 1
    options = calls[0][1]
    assert options["connect_args"] == {"connect_timeout": 3, "options": "-c statement_timeout=3000"}
    assert options["pool_timeout"] == 3
    assert options["pool_size"] == 2
    assert options["max_overflow"] == 0
    assert options["hide_parameters"] is True
    probe.check()
    engine.scalar = 2
    with pytest.raises(InfrastructureError, match="invalid data"):
        probe.check()
    engine.failure = True
    with pytest.raises(InfrastructureError) as error:
        probe.check()
    assert "SECRET" not in str(error.value)
    probe.close()
    assert engine.disposed


@pytest.mark.parametrize("url", ["bad", "sqlite:///:memory:"])
def test_production_adapter_rejects_unsupported_urls(url):
    with pytest.raises(ConfigurationError):
        PostgresConnectivity(url)


@pytest.mark.parametrize("timeout", [True, 0, 31, 1.5])
def test_adapter_timeout_configuration(timeout):
    with pytest.raises(ConfigurationError):
        PostgresConnectivity("postgresql+psycopg://u:p@localhost/test", timeout_seconds=timeout)


@pytest.mark.postgres
def test_actual_postgres_connectivity():
    url = os.environ.get("PARALLAX_TEST_DATABASE_URL")
    if url is None:
        pytest.skip(
            "PARALLAX_TEST_DATABASE_URL is not configured; no PostgreSQL success is inferred"
        )
    probe = PostgresConnectivity(url)
    try:
        probe.check()
    finally:
        probe.close()


def test_cli_version_config_and_run_context(capsys):
    assert main(["version"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "Parallax Risk"
    assert main(["config"]) == 0
    assert json.loads(capsys.readouterr().out)["database_configured"] is False
    assert main(["run-context"]) == 0
    captured = capsys.readouterr()
    context = json.loads(captured.out)
    log = json.loads(captured.err)
    assert context["run_id"] == log["run_id"]
    assert log["event"] == "run_context_created"
    assert context["seed"] == 0
    assert len(context["configuration_hash"]) == 64


def test_cli_failure_messages_redacted(monkeypatch, capsys):
    assert main(["check-db"]) == 1
    assert "not configured" in capsys.readouterr().err
    monkeypatch.setenv("PARALLAX_DATABASE_URL", "SECRET-invalid")
    assert main(["config"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SECRET" not in captured.err


def test_cli_database_check_and_cleanup(monkeypatch, capsys):
    monkeypatch.setenv("PARALLAX_DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
    state = {"closed": False, "failure": False}

    class Probe:
        def __init__(self, url, *, timeout_seconds):
            assert timeout_seconds == 5

        def check(self):
            if state["failure"]:
                raise InfrastructureError("PostgreSQL connectivity check failed")

        def close(self):
            state["closed"] = True

    monkeypatch.setattr("parallax_risk.cli.main.PostgresConnectivity", Probe)
    assert main(["check-db"]) == 0
    assert json.loads(capsys.readouterr().out) == {"database": "connected"}
    assert state["closed"]
    state.update(closed=False, failure=True)
    assert main(["check-db"]) == 1
    assert state["closed"]
    assert "check failed" in capsys.readouterr().err


def test_cli_help_and_version_start_without_settings(monkeypatch, capsys):
    monkeypatch.setenv("PARALLAX_DEFAULT_SEED", "invalid")
    for argument, expected in (("--help", "run-context"), ("--version", "Parallax Risk 0.2.0")):
        with pytest.raises(SystemExit) as result:
            main([argument])
        assert result.value.code == 0
        assert expected in capsys.readouterr().out
