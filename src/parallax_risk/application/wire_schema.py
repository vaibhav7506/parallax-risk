"""JSON Schema for exact nominal wire inputs, generated from server-selected types."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, Literal, TypeAliasType, Union, get_args, get_origin, get_type_hints

from parallax_risk.application.wire import declared_type
from parallax_risk.common.canonical import JsonValue


def schema(expected: type[object]) -> dict[str, JsonValue]:
    definitions: dict[str, JsonValue] = {}

    def build(annotation: Any) -> dict[str, JsonValue]:
        annotation = declared_type(annotation)
        if isinstance(annotation, TypeAliasType):
            return build(annotation.__value__)
        origin, args = get_origin(annotation), get_args(annotation)
        if origin in (Union, UnionType):
            return {"anyOf": [build(a) for a in args]}
        if origin is Literal:
            return {"enum": list(args)}
        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return {"type": "array", "items": build(args[0])}
            return {
                "type": "array",
                "prefixItems": [build(a) for a in args],
                "minItems": len(args),
                "maxItems": len(args),
            }
        if annotation is type(None):
            return {"type": "null"}
        if annotation in (str, int, bool, float):
            return {
                "type": {str: "string", int: "integer", bool: "boolean", float: "number"}[
                    annotation
                ]
            }
        if annotation is Decimal:
            return {
                "type": "string",
                "description": (
                    "Finite exact Decimal text; currency and monetary quantum are "
                    "validated separately."
                ),
            }
        if annotation in (date, datetime):
            return {"type": "string", "format": "date" if annotation is date else "date-time"}
        if annotation is bytes:
            return {
                "type": "object",
                "properties": {"base64": {"type": "string", "contentEncoding": "base64"}},
                "required": ["base64"],
                "additionalProperties": False,
            }
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return {"type": "string", "enum": [a.value for a in annotation]}
        if isinstance(annotation, type) and is_dataclass(annotation):
            name = annotation.__module__ + "." + annotation.__qualname__
            if name not in definitions:
                definitions[name] = {}
                hints = get_type_hints(annotation)
                properties: dict[str, JsonValue] = {"__type__": {"const": name}}
                properties.update(
                    {f.name: build(hints[f.name]) for f in fields(annotation) if f.init}
                )
                definitions[name] = {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                }
            return {"$ref": "#/$defs/" + name}
        raise TypeError("Unsupported declared wire annotation")

    root = build(expected)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **root, "$defs": definitions}
