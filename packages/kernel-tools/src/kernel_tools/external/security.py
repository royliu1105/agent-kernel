"""Fail-closed handling for external metadata and invocation boundaries."""

from __future__ import annotations

import json
import re
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from kernel_tools.errors import ToolError
from kernel_tools.external.config import ExternalAccess, ExternalToolContract
from kernel_tools.models import ToolExecutionContext, ToolMetadata


class ExternalToolError(ToolError):
    def __init__(self, message: str, *, error_type: str = "external_tool_error") -> None:
        super().__init__(message, error_type=error_type)


class ExternalConfigurationError(ValueError):
    """A remote catalog or operator configuration cannot be used safely."""


def require_access(access: ExternalAccess, context: ToolExecutionContext) -> None:
    allowed = (
        access.allow_unscoped
        if context.workspace_id is None
        else context.workspace_id in access.workspace_ids
    )
    if not allowed:
        raise ExternalToolError("External tool access denied.", error_type="external_access_denied")


def resolve_local_ref(value: Any, root: dict[str, Any], seen: tuple[str, ...] = ()) -> Any:
    if not isinstance(value, dict) or "$ref" not in value:
        return value
    ref = value["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen or len(seen) >= 12:
        raise ExternalConfigurationError("Only bounded, non-cyclic local references are supported.")
    target: Any = root
    try:
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
    except (KeyError, TypeError) as error:
        raise ExternalConfigurationError("Unresolved local reference.") from error
    if set(value) - {"$ref", "description", "summary"}:
        raise ExternalConfigurationError("Reference siblings are not supported.")
    return resolve_local_ref(target, root, (*seen, ref))


_ANNOTATIONS = {
    "title",
    "description",
    "default",
    "examples",
    "$comment",
    "$schema",
    "$defs",
    "definitions",
    "deprecated",
    "readOnly",
    "writeOnly",
    "example",
    "format",
}
_VALIDATION = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "const",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "nullable",
}
_PROPERTY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")


def sanitize_schema(
    schema: dict[str, Any], *, root: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Strip prose; retain bounded validation semantics, never fetch schema URLs."""
    if len(json.dumps(schema, ensure_ascii=True)) > 65_536:
        raise ExternalConfigurationError("External schema is too large.")
    document = root if root is not None else schema
    count = 0

    def clean(node: Any, depth: int = 0) -> Any:
        nonlocal count
        count += 1
        if depth > 12 or count > 512:
            raise ExternalConfigurationError("External schema is too complex.")
        node = resolve_local_ref(node, document)
        if isinstance(node, bool):
            return node
        if not isinstance(node, dict):
            raise ExternalConfigurationError("Malformed external schema.")
        result: dict[str, Any] = {}
        for key, value in node.items():
            if key in _ANNOTATIONS:
                continue
            if key not in _VALIDATION:
                raise ExternalConfigurationError("Unsupported external schema keyword.")
            if key == "properties":
                if not isinstance(value, dict) or any(not _PROPERTY.fullmatch(k) for k in value):
                    raise ExternalConfigurationError("Invalid external property name.")
                result[key] = {k: clean(v, depth + 1) for k, v in value.items()}
            elif key in {"items", "additionalProperties", "not"}:
                result[key] = clean(value, depth + 1)
            elif key in {"allOf", "anyOf", "oneOf"}:
                if not isinstance(value, list):
                    raise ExternalConfigurationError("Invalid schema composition.")
                result[key] = [clean(v, depth + 1) for v in value]
            elif key != "nullable":
                result[key] = value
        if node.get("nullable") is True:
            return {"anyOf": [result, {"type": "null"}]}
        return result

    try:
        sanitized = clean(schema)
        Draft202012Validator.check_schema(sanitized)
    except (SchemaError, RecursionError, TypeError) as error:
        raise ExternalConfigurationError("Invalid external JSON schema.") from error
    if not isinstance(sanitized, dict) or sanitized.get("type") != "object":
        raise ExternalConfigurationError("Tool input must be an object schema.")
    return sanitized


def metadata_for(contract: ExternalToolContract, schema: dict[str, Any]) -> ToolMetadata:
    return ToolMetadata(
        name=contract.name,
        description=contract.description,
        input_schema=schema,
        risk_level=contract.risk_level,
        timeout_ms=contract.timeout_ms,
        retry_safe=contract.retry_safe,
    )


def bounded_result(value: dict[str, Any], *, limit: int = 65_536) -> dict[str, Any]:
    if len(json.dumps(value, ensure_ascii=True).encode()) > limit:
        raise ExternalToolError("External result exceeds the configured limit.")
    return value
