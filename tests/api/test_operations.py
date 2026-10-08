from fastapi.testclient import TestClient

from parallax_risk import __version__
from parallax_risk.api.app import create_app
from parallax_risk.application.config import Settings
from parallax_risk.common.errors import InfrastructureError


class Probe:
    def __init__(self, available=True):
        self.available = available
        self.calls = 0
        self.closed = False

    def check(self):
        self.calls += 1
        if not self.available:
            raise InfrastructureError("safe failure")

    def close(self):
        self.closed = True


def test_health_version_and_readiness_without_database():
    with TestClient(create_app(Settings())) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json() == {"name": "Parallax Risk", "version": __version__, "phase": 6}
        ready = client.get("/ready")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready", "database": "not_configured"}
        assert set(client.get("/openapi.json").json()["paths"]) == {"/health", "/ready", "/version"}


def test_readiness_tracks_live_dependency_and_owns_lifecycle():
    probe = Probe()
    app = create_app(Settings(), connectivity=probe)
    with TestClient(app) as client:
        assert client.get("/ready").json() == {"status": "ready", "database": "connected"}
        probe.available = False
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "database": "unavailable"}
        assert client.get("/health").status_code == 200
        probe.available = True
        assert client.get("/ready").status_code == 200
    assert probe.calls == 3
    assert probe.closed
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_readiness_before_lifespan_is_not_success():
    client = TestClient(create_app(Settings(), connectivity=Probe()))
    assert client.get("/ready").status_code == 503


def test_factory_loads_settings_and_defers_engine_until_lifespan(monkeypatch):
    probe = Probe()
    calls = []

    def create_probe(url, *, timeout_seconds):
        calls.append((url, timeout_seconds))
        return probe

    monkeypatch.setenv("PARALLAX_DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
    monkeypatch.setattr("parallax_risk.api.app.PostgresConnectivity", create_probe)
    app = create_app()
    assert calls == []
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
    assert calls == [("postgresql+psycopg://u:p@localhost/test", 5)]
    assert probe.closed
