"""Validated boundary configuration; no settings are loaded at import time."""

import hashlib
import json
import os
import re
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from parallax_risk.common.errors import ConfigurationError
from parallax_risk.common.math import NumericalTolerance

MAX_SEED = 2**64 - 1


class ToleranceSettings(BaseModel):
    """Finite dimensionless foundation tolerances, not universal model tolerances."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    absolute: float = Field(default=1e-12, ge=0)
    relative: float = Field(default=1e-9, ge=0, lt=1)

    @field_validator("absolute", "relative", mode="before")
    @classmethod
    def reject_bool(cls, value: object) -> object:
        """Booleans are not numeric tolerances."""
        if isinstance(value, bool):
            raise ValueError("Tolerance cannot be boolean")
        return value

    @model_validator(mode="after")
    def validate_nonzero(self) -> Self:
        """Require at least one positive tolerance."""
        if self.absolute == self.relative == 0:
            raise ValueError("At least one tolerance must be positive")
        return self

    def to_domain(self) -> NumericalTolerance:
        """Create an independent domain tolerance value."""
        return NumericalTolerance(self.absolute, self.relative)


class Settings(BaseSettings):
    """Explicit runtime configuration; .env is never implicitly opened.

    PARALLAX_ environment variables override defaults. Nested tolerances use
    PARALLAX_TOLERANCES__ABSOLUTE/RELATIVE. Database credentials are secret and
    excluded from exported config and its hash (operational, not quantitative).
    """

    model_config = SettingsConfigDict(
        env_prefix="PARALLAX_",
        env_nested_delimiter="__",
        frozen=True,
        extra="forbid",
        allow_inf_nan=False,
        hide_input_in_errors=True,
    )
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    default_seed: int = Field(default=0, ge=0, le=MAX_SEED)
    tolerances: ToleranceSettings = Field(default_factory=ToleranceSettings)
    database_url: SecretStr | None = Field(default=None, exclude=True, repr=False)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)

    @field_validator("default_seed", "database_connect_timeout_seconds", mode="before")
    @classmethod
    def reject_bool(cls, value: object) -> object:
        """Boolean values must never become seeds or timeouts."""
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError("Integer configuration requires an integer or environment string")
        if isinstance(value, str) and not re.fullmatch(r"[0-9]+", value):
            raise ValueError("Integer environment configuration requires ASCII decimal digits")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_postgres(cls, value: SecretStr | None) -> SecretStr | None:
        """Allow explicit single-host PostgreSQL/psycopg URLs only."""
        if value is None:
            return None
        try:
            url = urlsplit(value.get_secret_value())
            valid = (
                url.scheme == "postgresql+psycopg"
                and bool(url.hostname)
                and bool(url.username)
                and bool(url.path.strip("/"))
                and not url.fragment
                and not url.query
                and (url.port is None or 1 <= url.port <= 65535)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Expected a single-host postgresql+psycopg URL without query/fragment")
        return value

    @model_validator(mode="after")
    def production_database(self) -> Self:
        """Production service must explicitly configure its PostgreSQL dependency."""
        if self.environment == "production" and self.database_url is None:
            raise ValueError("Production requires PostgreSQL configuration")
        return self

    def public_configuration(self) -> dict[str, object]:
        """Return a JSON-safe redacted configuration, safe for metadata and CLI."""
        result: dict[str, object] = self.model_dump(mode="json")
        result["database_configured"] = self.database_url is not None
        return result

    def configuration_hash(self) -> str:
        """SHA-256 of canonical, versioned, nonsecret effective configuration."""
        payload = {"schema_version": 1, "settings": self.public_configuration()}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_settings() -> Settings:
    """Load environment only when explicitly called; sanitize validation errors."""
    from pydantic import ValidationError
    from pydantic_settings.exceptions import SettingsError

    known = {"PARALLAX_" + field.upper() for field in Settings.model_fields}
    # The integration-test URL belongs to the test runner, not runtime settings.
    known.add("PARALLAX_TEST_DATABASE_URL")
    for name in os.environ:
        upper = name.upper()
        if upper.startswith("PARALLAX_") and (
            upper.split("__", 1)[0] not in known
            or ("__" in upper and not upper.startswith("PARALLAX_TOLERANCES__"))
        ):
            raise ConfigurationError("Unknown Parallax Risk configuration variable")
    try:
        return Settings()
    except (ValidationError, SettingsError):
        raise ConfigurationError("Invalid Parallax Risk configuration") from None
