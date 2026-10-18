"""ASGI limits/authentication/correlation without buffering unlimited request bodies."""

import time
from collections import deque
from threading import Lock
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from parallax_risk.api.service_schemas import Problem
from parallax_risk.application.access import Authenticator, ServiceError
from parallax_risk.application.service_config import ServiceSettings
from parallax_risk.application.wire import parse
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.logging import WorkflowLogger


def problem(status: int, code: str, correlation: str) -> bytes:
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        413: "Content Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Content",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    return (
        Problem(
            title=titles.get(status, "Request Failed"),
            status=status,
            detail=code,
            instance="urn:uuid:" + correlation,
            correlation_id=correlation,
        )
        .model_dump_json()
        .encode("utf-8")
    )


class RequestGuard:
    def __init__(
        self,
        app: ASGIApp,
        *,
        authenticator: Authenticator,
        settings: ServiceSettings,
        logger: WorkflowLogger,
    ) -> None:
        self.app, self.auth, self.settings, self.logger = app, authenticator, settings, logger
        self.rates: dict[str, deque[float]] = {}
        self.lock = Lock()

    def _rate(self, subject: str) -> None:
        now = time.monotonic()
        with self.lock:
            self.rates = {key: q for key, q in self.rates.items() if q and q[-1] > now - 60}
            if subject not in self.rates and len(self.rates) >= 256:
                raise ServiceError(429, "active_principal_limit_exceeded")
            queue = self.rates.setdefault(subject, deque())
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= self.settings.requests_per_minute:
                raise ServiceError(429, "request_rate_exceeded")
            queue.append(now)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation = str(uuid4())
        headers = scope.get("headers", [])
        ids = [v for k, v in headers if k.lower() == b"x-request-id"]

        async def guarded_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower()
                    not in (b"x-request-id", b"cache-control", b"x-content-type-options")
                ]
                response_headers.extend(
                    (
                        (b"x-request-id", correlation.encode("ascii")),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    )
                )
                message = {**message, "headers": response_headers}
                self.logger.event(
                    "http_request", run_id=correlation, outcome=str(message["status"])
                )
            await send(message)

        downstream_receive = receive
        try:
            if ids:
                if len(ids) != 1:
                    raise ServiceError(400, "invalid_request_correlation")
                candidate = ids[0].decode("ascii")
                if str(UUID(candidate)) != candidate:
                    raise ServiceError(400, "invalid_request_correlation")
                correlation = candidate
            scope.setdefault("state", {})["correlation_id"] = correlation
            if scope["path"].startswith("/v1/") or scope["path"] == "/v1":
                if self.settings.transport == "tls_proxy" and scope["scheme"] != "https":
                    raise ServiceError(403, "https_transport_required")
                keys = [v for k, v in headers if k.lower() == b"x-api-key"]
                if len(keys) != 1:
                    raise ServiceError(401, "authentication_required")
                principal = self.auth.authenticate(keys[0].decode("ascii"))
                self._rate(principal.subject)
                scope["state"]["principal"] = principal
                if scope["method"] in ("POST", "PUT", "PATCH"):
                    encodings = [v.lower() for k, v in headers if k.lower() == b"content-encoding"]
                    if encodings and encodings != [b"identity"]:
                        raise ServiceError(415, "compressed_request_not_supported")
                    types = [
                        v.split(b";", 1)[0].strip().lower()
                        for k, v in headers
                        if k.lower() == b"content-type"
                    ]
                    if types != [b"application/json"]:
                        raise ServiceError(415, "json_content_type_required")
                    body = bytearray()
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        body.extend(message.get("body", b""))
                        if len(body) > self.settings.maximum_payload_bytes:
                            raise ServiceError(413, "payload_limit_exceeded")
                        if not message.get("more_body", False):
                            break
                    parse(body.decode("utf-8"))
                    delivered = False

                    async def replay() -> Message:
                        nonlocal delivered
                        if delivered:
                            return await receive()
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}

                    downstream_receive = replay
        except ServiceError as error:
            await guarded_send(
                {
                    "type": "http.response.start",
                    "status": error.status,
                    "headers": [
                        (b"content-type", b"application/problem+json"),
                        (b"www-authenticate", b"ApiKey"),
                    ]
                    if error.status == 401
                    else [(b"content-type", b"application/problem+json")],
                }
            )
            await guarded_send(
                {
                    "type": "http.response.body",
                    "body": problem(error.status, error.code, correlation),
                }
            )
            return
        except (UnicodeError, ValueError, DomainValidationError):
            await guarded_send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [(b"content-type", b"application/problem+json")],
                }
            )
            await guarded_send(
                {
                    "type": "http.response.body",
                    "body": problem(400, "invalid_json_or_correlation", correlation),
                }
            )
            return
        # Downstream application failures retain their own 422/500 handlers; a
        # programming ValueError must never become an input error or second response.
        await self.app(scope, downstream_receive, guarded_send)
