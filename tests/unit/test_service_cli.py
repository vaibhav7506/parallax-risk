"""Actual loopback HTTP adapter, credential/file constraints and CLI protocol states."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from parallax_risk.cli.main import main
from parallax_risk.cli.service import SUBMIT
from parallax_risk.common.errors import ConfigurationError, InfrastructureError
from parallax_risk.infrastructure.http_client import ServiceClient, read_json

TOKEN = "synthetic-cli-token-" + "x" * 32


@pytest.fixture
def http(tmp_path):
    credential = tmp_path / "credential.txt"
    credential.write_text(TOKEN, encoding="ascii")
    payload = tmp_path / "input.json"
    payload.write_text('{"is_synthetic":true}', encoding="utf-8")
    state = {"requests": [], "responses": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def response(self):
            state["requests"].append(
                (
                    self.command,
                    self.path,
                    self.headers.get("X-API-Key"),
                    self.headers.get("Idempotency-Key"),
                )
            )
            if self.command == "POST":
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body, headers = (
                state["responses"].pop(0) if state["responses"] else (200, b'{"data":{}}', {})
            )
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        do_GET = response
        do_POST = response

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_port)
    try:
        yield url, credential, payload, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("command", list(SUBMIT))
def test_every_calculation_cli_posts_versioned_workflow(http, command, capsys):
    url, credential, payload, state = http
    assert (
        main(
            [
                command,
                "--server",
                url,
                "--credential-file",
                str(credential),
                "--input",
                str(payload),
                "--idempotency-key",
                "fixed",
            ]
        )
        == 0
    )
    assert state["requests"] == [("POST", "/v1/" + SUBMIT[command], TOKEN, "fixed")]
    assert json.loads(capsys.readouterr().out) == {"data": {}}


@pytest.mark.parametrize(
    "command,extra,path",
    [
        (
            "query",
            ["--path", "/v1/governance/model", "--limit", "2", "--after", "a"],
            "/v1/governance/model?after=a&limit=2",
        ),
        ("governance-write", [], "/v1/governance"),
        ("report", [], "/v1/reports"),
        ("ingest", ["--kind", "portfolio"], "/v1/portfolios"),
    ],
)
def test_read_governance_report_and_ingestion_cli(http, command, extra, path):
    url, credential, payload, state = http
    args = [command, "--server", url, "--credential-file", str(credential), *extra]
    if command != "query":
        args.extend(["--input", str(payload)])
    assert main(args) == 0 and state["requests"][0][1] == path


@pytest.mark.parametrize(
    "states,result",
    [
        (
            [
                {"data": {"job_id": "job"}},
                {"data": {"status": "running"}},
                {"data": {"status": "succeeded"}},
                {"data": {"result": 1}},
            ],
            0,
        ),
        ([{"data": {"job_id": "job"}}, {"data": {"status": "failed"}}], 1),
        ([None], 1),
        ([{"data": {}}], 1),
        ([{"data": {"job_id": "job"}}, None], 1),
    ],
)
def test_cli_polling_results_failures_and_invalid_protocol(http, states, result, capsys):
    url, credential, payload, state = http
    state["responses"] = [(200, json.dumps(x).encode(), {}) for x in states]
    assert (
        main(
            [
                "xva",
                "--server",
                url,
                "--credential-file",
                str(credential),
                "--input",
                str(payload),
                "--idempotency-key",
                "fixed",
                "--wait-seconds",
                "2",
            ]
        )
        == result
    )
    assert TOKEN not in capsys.readouterr().err


def test_cli_timeout_and_query_budget(http):
    url, credential, payload, state = http
    for extra in (["--wait-seconds", "-1"], ["--wait-seconds", "nan"]):
        assert (
            main(
                [
                    "xva",
                    "--server",
                    url,
                    "--credential-file",
                    str(credential),
                    "--input",
                    str(payload),
                    "--idempotency-key",
                    "fixed",
                    *extra,
                ]
            )
            == 1
        )
    state["responses"] = [
        (200, b'{"data":{"job_id":"job"}}', {}),
        (200, b'{"data":{"status":"queued"}}', {}),
    ]
    assert (
        main(
            [
                "xva",
                "--server",
                url,
                "--credential-file",
                str(credential),
                "--input",
                str(payload),
                "--idempotency-key",
                "fixed",
                "--wait-seconds",
                "0.001",
            ]
        )
        == 1
    )
    assert (
        main(
            [
                "query",
                "--server",
                url,
                "--credential-file",
                str(credential),
                "--path",
                "/v1/runs?x=1",
                "--limit",
                "2",
            ]
        )
        == 1
    )


def test_http_redirect_never_sends_secret_to_other_origin_and_html_is_text(http):
    url, credential, _, state = http
    client = ServiceClient(url, str(credential))
    state["responses"] = [(302, b"", {"Location": "http://example.invalid/steal"})]
    with pytest.raises(InfrastructureError, match="302"):
        client.request("GET", "/v1/me")
    assert len(state["requests"]) == 1
    state["responses"] = [(200, b"<html>synthetic</html>", {})]
    assert client.text("/v1/reports/report/html") == "<html>synthetic</html>"
    with pytest.raises(ConfigurationError):
        client.request("GET", "/outside")


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.example",
        "https://user:SECRET@example.test",
        "file:///x",
        "http://localhost:SECRET",
        "https://example.test:0",
        "https://[malformed",
        "https://example.test/path",
    ],
)
def test_url_policy_rejects_remote_plaintext_credentials_and_paths(tmp_path, url):
    with pytest.raises(ConfigurationError):
        ServiceClient(url, str(tmp_path / "absent"))


def test_file_limits_encoding_and_credentials_are_explicit(tmp_path):
    source = tmp_path / "input"
    source.write_bytes(b"{}")
    assert read_json(str(source)) == {}
    with pytest.raises(ConfigurationError):
        read_json(str(source), 1)
    source.write_bytes(b"\xff")
    with pytest.raises(ConfigurationError):
        read_json(str(source))
    with pytest.raises(ConfigurationError):
        read_json(str(tmp_path / "absent"))
    for data in (
        b"short",
        b"x" * 300,
        b"\xff" * 32,
        b"x" * 32 + b" ",
        b"x" * 256 + b"\n\nSECRET",
        b"x" * 31 + b"\x00",
    ):
        source.write_bytes(data)
        with pytest.raises(ConfigurationError):
            ServiceClient("http://localhost", str(source))
    source.write_text(TOKEN, encoding="ascii")
    with pytest.raises(ConfigurationError):
        ServiceClient("http://localhost", str(source), timeout=0)
    with pytest.raises(ConfigurationError):
        ServiceClient("http://localhost", str(tmp_path))


def test_invalid_service_encoding_is_a_sanitized_protocol_failure(http):
    url, credential, _, state = http
    client = ServiceClient(url, str(credential))
    for retrieve in (client.request,):
        state["responses"] = [(200, b"\xffSECRET", {})]
        with pytest.raises(InfrastructureError, match="Invalid service JSON encoding"):
            retrieve("GET", "/v1/me")
    state["responses"] = [(200, b"\xffSECRET", {})]
    with pytest.raises(InfrastructureError, match="Invalid service text encoding"):
        client.text("/v1/reports/report/html")


def test_invalid_idempotency_header_fails_before_http_request(http):
    url, credential, _, state = http
    client = ServiceClient(url, str(credential))
    for key in ("", "x" * 129, "valid\r\nX-API-Key: SECRET", "\xff"):
        with pytest.raises(ConfigurationError, match="Invalid idempotency header"):
            client.request("POST", "/v1/xva", {}, idempotency_key=key)
    assert state["requests"] == []
