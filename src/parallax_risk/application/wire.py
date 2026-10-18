"""Schema-1 nominal JSON boundary; never imports types named by a client.

The server supplies the expected annotation. Dataclass constructors remain the
economic validation boundary. JSON parsing rejects duplicate keys and nonfinite
values; decoding never uses pickle, eval, filesystem access or dynamic imports.
"""

import base64
import json
import math
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import UnionType
from typing import Any, Literal, TypeAliasType, Union, cast, get_args, get_origin, get_type_hints

from parallax_risk.common.canonical import JsonValue
from parallax_risk.common.errors import DomainValidationError, ParallaxError
from parallax_risk.common.time import utc_timestamp
from parallax_risk.domain.credit.dependence import ReducedFormSpread, StochasticCreditSpread
from parallax_risk.domain.governance.contracts import Document


def declared_type(annotation: Any) -> Any:
    """Explicit concrete allowlist for protocol fields; no client type resolution."""
    return ReducedFormSpread if annotation is StochasticCreditSpread else annotation


def value(item: object) -> JsonValue:
    """Portable nominal representation, including bounded immutable binary arrays."""
    if isinstance(item, Enum):
        return value(item.value)
    if item is None or type(item) in (str, bool, int):
        return cast(JsonValue, item)
    if isinstance(item, float):
        if not math.isfinite(item):
            raise DomainValidationError("Wire numbers must be finite")
        return item
    if isinstance(item, Decimal):
        if not item.is_finite():
            raise DomainValidationError("Wire decimals must be finite")
        return str(item)
    if isinstance(item, datetime):
        return utc_timestamp(item).isoformat()
    if isinstance(item, date):
        return item.isoformat()
    if isinstance(item, bytes):
        return {"base64": base64.b64encode(item).decode("ascii")}
    if isinstance(item, tuple):
        return [value(x) for x in item]
    if isinstance(item, dict) and all(isinstance(k, str) for k in item):
        return {k: value(v) for k, v in item.items()}
    if is_dataclass(item) and not isinstance(item, type):
        return {
            "__type__": type(item).__module__ + "." + type(item).__qualname__,
            **{f.name: value(getattr(item, f.name)) for f in fields(item) if f.init},
        }
    raise DomainValidationError("Unsupported wire value")


def document(item: object) -> Document:
    """Canonical immutable envelope; arrays are frozen by Document's JSON parser."""
    return Document(json.dumps({"value": value(item)}, allow_nan=False, separators=(",", ":")))


def parse(text: str, *, maximum_nodes: int = 100_000, maximum_depth: int = 48) -> JsonValue:
    """Strict JSON for file/API ingestion, with structural limits before decoding."""

    def pairs(items: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for key, item in items:
            if key in result:
                raise DomainValidationError("Duplicate JSON keys")
            result[key] = item
        return result

    def constant(_: str) -> None:
        raise DomainValidationError("Nonfinite JSON numbers")

    try:
        root: JsonValue = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError):
        raise DomainValidationError("Invalid JSON") from None
    stack = [(root, 0)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > maximum_nodes or depth > maximum_depth:
            raise DomainValidationError("JSON structural limit exceeded")
        if isinstance(node, float) and not math.isfinite(node):
            raise DomainValidationError("Nonfinite JSON numbers")
        if isinstance(node, list):
            stack.extend((x, depth + 1) for x in node)
        elif isinstance(node, dict):
            stack.extend((x, depth + 1) for x in node.values())
    return root


def decode[T](item: JsonValue, expected: type[T]) -> T:
    """Decode only the exact server-selected root and its declared nested types."""
    try:
        return cast(T, _decode(item, expected))
    except (ValueError, TypeError, KeyError, OverflowError, InvalidOperation, ParallaxError):
        raise DomainValidationError("Invalid typed wire input") from None


def _decode(item: JsonValue, expected: Any) -> Any:
    expected = declared_type(expected)
    if isinstance(expected, TypeAliasType):
        return _decode(item, expected.__value__)
    origin, args = get_origin(expected), get_args(expected)
    if origin in (Union, UnionType):
        for alternative in args:
            try:
                return _decode(item, alternative)
            except (
                ValueError,
                TypeError,
                KeyError,
                OverflowError,
                InvalidOperation,
                ParallaxError,
            ):
                continue
        raise ValueError("No declared union member")
    if origin is Literal:
        if any(type(item) is type(a) and item == a for a in args):
            return item
        raise ValueError("Invalid literal")
    if origin is tuple:
        if not isinstance(item, list):
            raise ValueError("Expected array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(x, args[0]) for x in item)
        if len(args) != len(item):
            raise ValueError("Fixed tuple arity")
        return tuple(_decode(x, t) for x, t in zip(item, args, strict=True))
    if expected is type(None) and item is None:
        return None
    if expected in (str, int, bool) and type(item) is expected:
        return item
    if (
        expected is float
        and type(item) in (int, float)
        and math.isfinite(float(cast(int | float, item)))
    ):
        return float(cast(int | float, item))
    if expected is Decimal and isinstance(item, str):
        result = Decimal(item)
        if result.is_finite():
            return result
    if expected is datetime and isinstance(item, str):
        return utc_timestamp(datetime.fromisoformat(item))
    if expected is date and isinstance(item, str):
        result_date = date.fromisoformat(item)
        if result_date.isoformat() == item:
            return result_date
    if expected is bytes and isinstance(item, dict) and set(item) == {"base64"}:
        return base64.b64decode(cast(str, item["base64"]), validate=True)
    if isinstance(expected, type) and issubclass(expected, Enum) and type(item) is str:
        return expected(item)
    if isinstance(expected, type) and is_dataclass(expected) and isinstance(item, dict):
        hints = get_type_hints(expected)
        names = {f.name for f in fields(expected) if f.init}
        nominal = expected.__module__ + "." + expected.__qualname__
        if set(item) != names | {"__type__"} or item["__type__"] != nominal:
            raise ValueError("Exact nominal fields required")
        return expected(**{n: _decode(item[n], hints[n]) for n in names})
    raise ValueError("Type mismatch")
