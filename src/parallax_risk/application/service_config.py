"""Explicit operational service configuration; separate from financial settings hashes."""

from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from parallax_risk.application.access import Principal, Role
from parallax_risk.application.wire import parse
from parallax_risk.common.errors import ConfigurationError
from parallax_risk.domain.xva.contracts import fingerprint


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PARALLAX_SERVICE_", frozen=True, extra="forbid", hide_input_in_errors=True
    )
    credentials: SecretStr | None = Field(default=None, exclude=True, repr=False)
    origins: tuple[str, ...] = ()
    maximum_payload_bytes: int = Field(default=1024 * 1024, ge=1024, le=4 * 1024 * 1024)
    requests_per_minute: int = Field(default=120, ge=1, le=10000)
    workers: int = Field(default=1, ge=1, le=4)
    maximum_pending_jobs: int = Field(default=64, ge=1, le=256)
    transport: Literal["local", "tls_proxy"] = "local"

    @field_validator(
        "maximum_payload_bytes",
        "requests_per_minute",
        "workers",
        "maximum_pending_jobs",
        mode="before",
    )
    @classmethod
    def reject_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Integer service settings cannot be booleans")
        return value

    @model_validator(mode="after")
    def secure(self) -> Self:
        for origin in self.origins:
            parts = urlsplit(origin)
            if (
                parts.scheme not in ("http", "https")
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.path
                or parts.query
                or parts.fragment
                or origin.endswith(":")
            ):
                raise ValueError("CORS requires exact explicit HTTP origins")
            if self.transport == "tls_proxy" and parts.scheme != "https":
                raise ValueError("TLS-proxy origins must use HTTPS")
        if len(set(self.origins)) != len(self.origins):
            raise ValueError("Duplicate CORS origins")
        if self.credentials is not None:
            self.entries()
        return self

    def entries(self) -> tuple[tuple[str, Principal], ...]:
        if self.credentials is None:
            return ()
        try:
            data = parse(self.credentials.get_secret_value(), maximum_nodes=4096, maximum_depth=4)
            if not isinstance(data, list) or not 1 <= len(data) <= 256:
                raise ValueError("Credential count")
            result: list[tuple[str, Principal]] = []
            for item in data:
                if not isinstance(item, dict) or set(item) != {"sha256", "subject", "roles"}:
                    raise ValueError("Credential fields")
                digest, subject, roles = item["sha256"], item["subject"], item["roles"]
                if (
                    not isinstance(digest, str)
                    or not isinstance(subject, str)
                    or not isinstance(roles, list)
                    or any(not isinstance(r, str) for r in roles)
                    or len(set(roles)) != len(roles)
                ):
                    raise ValueError("Credential types")
                fingerprint(digest)
                result.append((digest, Principal(subject, frozenset(Role(str(r)) for r in roles))))
            if len({d for d, _ in result}) != len(result) or len(
                {p.subject for _, p in result}
            ) != len(result):
                raise ValueError("Duplicate credentials/subjects")
            return tuple(result)
        except Exception:
            # This configuration boundary never exports input-bearing validation errors.
            raise ConfigurationError("Invalid service credential configuration") from None


def load_service_settings() -> ServiceSettings:
    try:
        return ServiceSettings()
    except Exception:
        raise ConfigurationError("Invalid service configuration") from None
