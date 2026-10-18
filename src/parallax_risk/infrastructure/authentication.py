"""Local API-key verifier using configured digests; replaceable through the port."""

import hashlib
import hmac
from dataclasses import dataclass

from parallax_risk.application.access import Principal, ServiceError


@dataclass(frozen=True, slots=True)
class DigestAuthenticator:
    entries: tuple[tuple[str, Principal], ...]

    def authenticate(self, token: str | None) -> Principal:
        if token is None or not 32 <= len(token) <= 256 or not token.isascii():
            raise ServiceError(401, "authentication_required")
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        principal = None
        for expected, candidate in self.entries:
            if hmac.compare_digest(digest, expected):
                principal = candidate
        if principal is None:
            raise ServiceError(401, "authentication_required")
        return principal
