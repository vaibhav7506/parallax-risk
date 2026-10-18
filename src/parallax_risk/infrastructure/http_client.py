"""Explicit bounded HTTP/file adapter used by the production CLI and examples."""

import ipaddress
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

from parallax_risk.application.wire import parse
from parallax_risk.common.canonical import JsonValue
from parallax_risk.common.errors import ConfigurationError, InfrastructureError


def read_json(path: str, maximum_bytes: int = 1024 * 1024) -> JsonValue:
    source = Path(path)
    try:
        if source.is_symlink() or not source.is_file():
            raise ConfigurationError("Input must be a regular local file")
        with source.open("rb") as stream:
            raw = stream.read(maximum_bytes + 1)
        if len(raw) > maximum_bytes:
            raise ConfigurationError("Input file exceeds byte limit")
        return parse(raw.decode("utf-8"))
    except (OSError, UnicodeError):
        raise ConfigurationError("Cannot read UTF-8 input file") from None


class ServiceClient:
    def __init__(self, url: str, credential_file: str, timeout: float = 15.0) -> None:
        try:
            parts = urlsplit(url)
            if parts.port is not None and not 1 <= parts.port <= 65535:
                raise ValueError("Invalid port")
        except ValueError:
            raise ConfigurationError("Invalid service URL") from None
        try:
            loopback = (
                parts.hostname == "localhost"
                or ipaddress.ip_address(parts.hostname or "").is_loopback
            )
        except ValueError:
            loopback = False
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or (parts.scheme == "http" and not loopback)
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in ("", "/")
        ):
            raise ConfigurationError(
                "Server requires HTTPS or loopback HTTP without URL credentials"
            )
        source = Path(credential_file)
        try:
            if source.is_symlink() or not source.is_file():
                raise ConfigurationError("Credential must be a regular local file")
            with source.open("rb") as stream:
                raw = stream.read(259)
            if len(raw) > 258:
                raise ConfigurationError("Credential file exceeds byte limit")
            token = raw.decode("ascii").rstrip("\r\n")
            if not 32 <= len(token) <= 256 or any(not 33 <= ord(c) <= 126 for c in token):
                raise ConfigurationError("Invalid credential file")
        except (OSError, UnicodeError):
            raise ConfigurationError("Cannot read credential file") from None
        if not 0 < timeout <= 60:
            raise ConfigurationError("HTTP timeout must be in (0,60] seconds")
        self.url, self._token, self.timeout = url.rstrip("/"), token, timeout

    def request(
        self,
        method: str,
        path: str,
        payload: JsonValue = None,
        *,
        idempotency_key: str | None = None,
    ) -> JsonValue:
        try:
            return parse(
                self._bytes(method, path, payload, idempotency_key).decode("utf-8"),
                maximum_nodes=1_000_000,
            )
        except UnicodeError:
            raise InfrastructureError("Invalid service JSON encoding") from None

    def text(self, path: str) -> str:
        """Retrieve a bounded authenticated HTML report without executing its content."""
        try:
            return self._bytes("GET", path, None, None).decode("utf-8")
        except UnicodeError:
            raise InfrastructureError("Invalid service text encoding") from None

    def _bytes(
        self, method: str, path: str, payload: JsonValue, idempotency_key: str | None
    ) -> bytes:
        if not path.startswith("/v1/") or path.startswith("//") or "#" in path:
            raise ConfigurationError("Only versioned service paths are accepted")
        headers = {"X-API-Key": self._token, "Content-Type": "application/json"}
        if idempotency_key is not None:
            if not 1 <= len(idempotency_key) <= 128 or any(
                not 33 <= ord(c) <= 126 for c in idempotency_key
            ):
                raise ConfigurationError("Invalid idempotency header")
            headers["Idempotency-Key"] = idempotency_key
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode("utf-8")
        if body is not None and len(body) > 1024 * 1024:
            raise ConfigurationError("Request exceeds CLI byte limit")
        request = Request(self.url + path, data=body, headers=headers, method=method)
        try:
            # Redirects must not carry API credentials to another origin.
            from urllib.request import HTTPRedirectHandler, build_opener

            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(
                    self, req: Request, fp: object, code: int, msg: str, hdrs: object, newurl: str
                ) -> None:
                    return None

            with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                raw = response.read(64 * 1024 * 1024 + 1)
                if len(raw) > 64 * 1024 * 1024:
                    raise InfrastructureError("Response exceeds CLI byte limit")
                return bytes(raw)
        except HTTPError as error:
            raise InfrastructureError(f"Service rejected request (HTTP {error.code})") from None
        except (URLError, OSError, UnicodeError, ValueError):
            raise InfrastructureError("Service request failed") from None
