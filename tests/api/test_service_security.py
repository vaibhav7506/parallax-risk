"""Fail-closed authentication, bounded bodies, TLS, CORS and safe problems."""

import asyncio
import hashlib
import io
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from parallax_risk.api.app import create_app
from parallax_risk.api.guard import RequestGuard
from parallax_risk.application.access import Principal, Role, ServiceError
from parallax_risk.application.config import Settings
from parallax_risk.application.service_config import ServiceSettings, load_service_settings
from parallax_risk.common.errors import ConfigurationError
from parallax_risk.common.logging import create_logger
from parallax_risk.infrastructure.authentication import DigestAuthenticator

TOKEN = "synthetic-security-test-" + "x" * 32
USER = Principal("reader", frozenset({Role.READER}))
AUTH = DigestAuthenticator(((hashlib.sha256(TOKEN.encode()).hexdigest(), USER),))


def app(settings=None):
    return create_app(
        Settings(), authenticator=AUTH, service_settings=settings or ServiceSettings()
    )


def test_authentication_correlation_contract_problem_details_and_fail_closed_service():
    with TestClient(app()) as client:
        assert client.get("/v1/me").status_code == 401
        assert client.get("/v1/me", headers={"X-API-Key": "bad"}).status_code == 401
        correlation = str(uuid4())
        response = client.get("/v1/me", headers={"X-API-Key": TOKEN, "X-Request-ID": correlation})
        assert response.status_code == 200 and response.headers["x-request-id"] == correlation
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        failed = client.get("/v1/runs", headers={"X-API-Key": TOKEN})
        assert (
            failed.status_code == 503
            and failed.headers["content-type"] == "application/problem+json"
        )
        assert failed.json()["correlation_id"] == failed.headers["x-request-id"]
        assert TOKEN not in failed.text
        assert (
            client.get("/v1/me", headers={"X-API-Key": TOKEN, "X-Request-ID": "bad"}).status_code
            == 400
        )
        assert (
            client.get("/v1/me", headers=[("X-API-Key", TOKEN), ("X-API-Key", TOKEN)]).status_code
            == 401
        )
        assert (
            client.get(
                "/health", headers=[("X-Request-ID", correlation), ("X-Request-ID", correlation)]
            ).status_code
            == 400
        )
        assert client.get("/v1/unknown", headers={"X-API-Key": TOKEN}).status_code == 404


@pytest.mark.parametrize(
    "body,headers,status",
    [
        ("{}", {}, 415),
        ("{}", {"Content-Type": "text/plain"}, 415),
        ("{}", {"Content-Type": "application/json", "Content-Encoding": "gzip"}, 415),
        ('{"a":1,"a":2}', {"Content-Type": "application/json"}, 400),
        ('{"secret":NaN}', {"Content-Type": "application/json"}, 400),
        ('{"secret":1e400}', {"Content-Type": "application/json"}, 400),
        ("x" * 1025, {"Content-Type": "application/json"}, 413),
        ("{}", {"Content-Type": "application/json"}, 422),
    ],
)
def test_actual_stream_body_limit_strict_json_and_pydantic_envelopes(body, headers, status):
    with TestClient(app(ServiceSettings(maximum_payload_bytes=1024))) as client:
        response = client.post(
            "/v1/xva",
            content=body,
            headers={"X-API-Key": TOKEN, "Idempotency-Key": "example", **headers},
        )
        assert response.status_code == status
        assert "secret" not in response.text


def test_explicit_cors_tls_transport_and_rate_limit():
    settings = ServiceSettings(
        transport="tls_proxy", origins=("https://research.example",), requests_per_minute=1
    )
    with TestClient(app(settings), base_url="http://localhost") as client:
        assert client.get("/v1/me", headers={"X-API-Key": TOKEN}).status_code == 403
    with TestClient(app(settings), base_url="https://localhost") as client:
        good = client.get(
            "/v1/me", headers={"X-API-Key": TOKEN, "Origin": "https://research.example"}
        )
        assert good.headers["access-control-allow-origin"] == "https://research.example"
        rejected = client.get(
            "/v1/me", headers={"X-API-Key": TOKEN, "Origin": "https://untrusted.example"}
        )
        assert rejected.status_code == 429 and "access-control-allow-origin" not in rejected.headers
        preflight = client.options(
            "/v1/me",
            headers={
                "Origin": "https://research.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )
        assert preflight.status_code == 200


@pytest.mark.parametrize(
    "configuration",
    [
        {"origins": ("*",)},
        {"origins": ("https://user:pass@example.test",)},
        {"origins": ("https://example.test/path",)},
        {"origins": ("https://example.test",) * 2},
        {"transport": "tls_proxy", "origins": ("http://example.test",)},
        {"workers": True},
        {"workers": 0},
        {"maximum_payload_bytes": 0},
    ],
)
def test_secure_configuration_rejects_ambiguity(configuration):
    with pytest.raises(ValidationError):
        ServiceSettings(**configuration)


@pytest.mark.parametrize(
    "credential",
    [
        "SECRET",
        "[]",
        "[{}]",
        '[{"sha256":"SECRET","subject":"user","roles":["reader"]}]',
        '[{"sha256":"' + "a" * 64 + '","subject":"user","roles":[]}]',
    ],
)
def test_credentials_never_export_invalid_inputs(credential, monkeypatch):
    monkeypatch.setenv("PARALLAX_SERVICE_CREDENTIALS", credential)
    with pytest.raises(ConfigurationError) as error:
        load_service_settings()
    assert "SECRET" not in str(error.value)


def test_valid_digest_credentials_redaction_production_gate_and_role_checks():
    raw = json.dumps(
        [
            {
                "sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
                "subject": "reader",
                "roles": ["reader"],
            }
        ]
    )
    settings = ServiceSettings(credentials=SecretStr(raw))
    assert "credentials" not in settings.model_dump() and TOKEN not in repr(settings)
    assert DigestAuthenticator(settings.entries()).authenticate(TOKEN) == USER
    for token in (None, "x" * 300, "£" * 32):
        with pytest.raises(ServiceError):
            AUTH.authenticate(token)
    with pytest.raises(ServiceError):
        USER.require(Role.APPROVER)
    with pytest.raises(ConfigurationError):
        create_app(
            Settings(
                environment="production", database_url="postgresql+psycopg://u:p@localhost/test"
            ),
            service_settings=ServiceSettings(),
        )
    with pytest.raises(ConfigurationError):
        create_app(Settings(), service_settings=settings)


def test_raw_asgi_chunked_limit_disconnect_non_http_and_programming_failure():
    called = []

    async def downstream(scope, receive, send):
        called.append(scope["type"])
        if scope["path"] == "/v1/failure":
            raise ValueError("SECRET programming failure")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    guard = RequestGuard(
        downstream,
        authenticator=AUTH,
        settings=ServiceSettings(maximum_payload_bytes=1024),
        logger=create_logger(stream=io.StringIO()),
    )
    scope = {
        "type": "http",
        "path": "/v1/xva",
        "scheme": "http",
        "method": "POST",
        "headers": [(b"x-api-key", TOKEN.encode()), (b"content-type", b"application/json")],
    }

    async def execute(messages, scope=scope):
        output = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            output.append(message)

        await guard(dict(scope), receive, send)
        return output

    output = asyncio.run(
        execute(
            [
                {"type": "http.request", "body": b"x" * 512, "more_body": True},
                {"type": "http.request", "body": b"x" * 513, "more_body": False},
            ]
        )
    )
    assert output[0]["status"] == 413 and not called
    assert asyncio.run(execute([{"type": "http.disconnect"}])) == []
    with pytest.raises(ValueError, match="programming"):
        asyncio.run(
            execute([{"type": "http.request", "body": b"{}"}], {**scope, "path": "/v1/failure"})
        )
    asyncio.run(execute([], {**scope, "type": "websocket"}))
    assert called[-1] == "websocket"
