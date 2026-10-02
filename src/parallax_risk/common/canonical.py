"""Versioned JSON content fingerprints, without pickle or mutable caches."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.math import require_finite
from parallax_risk.common.time import utc_timestamp

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]


def canonical_value(value: object) -> JsonValue:
    """Serialize trusted value objects explicitly; tuples become JSON arrays.

    Decimal uses exact text, date uses ISO format, instants normalize to UTC.
    Dataclasses include their qualified type to preserve nominal distinctions.
    Unsupported objects and NaN/Inf are rejected rather than stringified.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return require_finite(value, name="canonical float")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DomainValidationError("Canonical decimal must be finite")
        return str(value)
    if isinstance(value, datetime):
        return utc_timestamp(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, tuple):
        return [canonical_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise DomainValidationError("Canonical object keys must be strings")
        return {key: canonical_value(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, JsonValue] = {
            "__type__": type(value).__module__ + "." + type(value).__qualname__
        }
        result.update(
            {field.name: canonical_value(getattr(value, field.name)) for field in fields(value)}
        )
        return result
    raise DomainValidationError("Unsupported canonical metadata type")


def content_hash(value: object) -> str:
    """SHA-256 of canonical type-aware JSON, using content-fingerprint schema 1."""
    encoded = json.dumps(
        {"schema_version": 1, "content": canonical_value(value)},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
