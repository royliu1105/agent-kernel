"""Generate allowlisted HTTP tools from a bounded OpenAPI JSON document."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator

from kernel_tools.errors import ToolTimeoutError, ToolValidationError
from kernel_tools.external.config import OpenAPIBinding, OpenAPIConfig
from kernel_tools.external.http import approved_url, validate_path
from kernel_tools.external.security import (
    ExternalConfigurationError,
    ExternalToolError,
    bounded_result,
    metadata_for,
    require_access,
    resolve_local_ref,
    sanitize_schema,
)
from kernel_tools.models import ToolExecutionContext, ToolMetadata

_METHODS = {"get", "head", "post", "put", "patch", "delete", "options"}
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_.-]{0,63})\}")


class OpenAPITool:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        config: OpenAPIConfig,
        binding: OpenAPIBinding,
        method: str,
        path: str,
        schema: dict[str, Any],
    ) -> None:
        self._client = client
        self._config = config
        self._binding = binding
        self._method = method.upper()
        self._path = path
        self._metadata = metadata_for(binding.contract, schema)
        self._active = True
        if binding.contract.read_only and method not in {"get", "head", "options"}:
            raise ExternalConfigurationError("Mutating HTTP methods cannot be marked read-only.")
        if binding.idempotency_header:
            header = binding.idempotency_header.lower()
            if header != "idempotency-key" and not header.startswith("x-idempotency-"):
                raise ExternalConfigurationError("Use an explicit idempotency-only HTTP header.")
            if header in {name.lower() for name in config.endpoint.headers}:
                raise ExternalConfigurationError("Idempotency header conflicts with credentials.")

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata.model_copy(deep=True)

    def deactivate(self) -> None:
        self._active = False

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.execute_with_context(arguments, context=ToolExecutionContext())

    async def execute_with_context(
        self, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        require_access(self._config.access, context)
        if not self._active:
            raise ExternalToolError("External tool lifecycle is closed.")
        if not Draft202012Validator(self._metadata.input_schema).is_valid(arguments):
            raise ToolValidationError(self._metadata.name, "Invalid OpenAPI operation arguments.")
        if len(json.dumps(arguments).encode()) > 65_536:
            raise ToolValidationError(self._metadata.name, "External request is too large.")
        path = self._path
        for name, value in arguments.get("path", {}).items():
            text = _scalar(value)
            if (
                text in {".", ".."}
                or any(char in text for char in "/\\%?#")
                or any(ord(char) < 32 for char in text)
            ):
                raise ToolValidationError(self._metadata.name, "Unsafe path argument.")
            path = path.replace("{" + name + "}", quote(text, safe=""))
        base = str(approved_url(self._config.endpoint)).rstrip("/")
        headers: dict[str, str] = {}
        if self._binding.idempotency_header:
            if context.tool_call_id is None:
                raise ExternalToolError("This operation requires a persisted tool call identity.")
            headers[self._binding.idempotency_header] = str(context.tool_call_id)
        query = {name: _scalar(value) for name, value in arguments.get("query", {}).items()}
        try:
            async with self._client.stream(
                self._method,
                base + path,
                params=query,
                headers=headers,
                **({"json": arguments["body"]} if "body" in arguments else {}),
                timeout=self._metadata.timeout_ms / 1_000,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise ExternalToolError(
                        f"External HTTP operation returned {response.status_code}."
                    )
                data = await response.aread()
                content: Any
                if not data:
                    content = None
                elif "json" in response.headers.get("content-type", ""):
                    content = json.loads(data)
                else:
                    content = data.decode("utf-8")
                return bounded_result(
                    {
                        "source": self._config.name,
                        "untrusted": True,
                        "status_code": response.status_code,
                        "data": content,
                    }
                )
        except httpx.TimeoutException as error:
            raise ToolTimeoutError(self._metadata.name, self._metadata.timeout_ms) from error
        except ExternalToolError:
            raise
        except Exception:
            raise ExternalToolError("External HTTP operation failed.") from None


def _scalar(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def load_openapi_tools(client: httpx.AsyncClient, config: OpenAPIConfig) -> list[OpenAPITool]:
    with config.document.open("rb") as stream:
        data = stream.read(1_048_577)
    if len(data) > 1_048_576:
        raise ExternalConfigurationError("OpenAPI document exceeds 1 MiB.")
    try:
        document = json.loads(data)
    except (ValueError, RecursionError) as error:
        raise ExternalConfigurationError("OpenAPI document must be valid JSON.") from error
    if not isinstance(document, dict) or not re.fullmatch(
        r"3\.(0|1)\.\d+", str(document.get("openapi", ""))
    ):
        raise ExternalConfigurationError("Supported OpenAPI versions are 3.0 and 3.1.")
    paths = document.get("paths", {})
    if not isinstance(paths, dict) or len(paths) > 1_000:
        raise ExternalConfigurationError("Invalid or oversized OpenAPI paths.")
    operations: dict[str, tuple[str, str, dict[str, Any], dict[str, Any]]] = {}
    for path, raw_path_item in paths.items():
        validate_path(path)
        if "?" in path or "#" in path:
            raise ExternalConfigurationError("OpenAPI paths cannot contain queries or fragments.")
        item = resolve_local_ref(raw_path_item, document)
        if not isinstance(item, dict):
            raise ExternalConfigurationError("Invalid OpenAPI path item.")
        for method, operation in item.items():
            if method not in _METHODS:
                continue
            if not isinstance(operation, dict):
                raise ExternalConfigurationError("Invalid OpenAPI operation.")
            name = operation.get("operationId")
            if not isinstance(name, str):
                continue
            if name in operations:
                raise ExternalConfigurationError("Duplicate OpenAPI operationId.")
            operations[name] = (method, path, item, operation)
    tools: list[OpenAPITool] = []
    for binding in config.bindings:
        if binding.operation_id not in operations:
            raise ExternalConfigurationError("Configured OpenAPI operation is missing.")
        method, path, item, operation = operations[binding.operation_id]
        schema = _input_schema(path, item, operation, document)
        tools.append(
            OpenAPITool(
                client=client,
                config=config,
                binding=binding,
                method=method,
                path=path,
                schema=schema,
            )
        )
    return tools


def _input_schema(
    path: str,
    path_item: dict[str, Any],
    operation: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    params: dict[tuple[str, str], dict[str, Any]] = {}
    for source in (path_item, operation):
        raw_parameters = source.get("parameters", [])
        if not isinstance(raw_parameters, list) or len(raw_parameters) > 100:
            raise ExternalConfigurationError("Invalid OpenAPI parameters.")
        seen: set[tuple[str, str]] = set()
        for raw in raw_parameters:
            parameter = resolve_local_ref(raw, document)
            if not isinstance(parameter, dict):
                raise ExternalConfigurationError("Invalid OpenAPI parameter.")
            name, location = parameter.get("name"), parameter.get("in")
            if not isinstance(name, str) or location not in {"path", "query"}:
                raise ExternalConfigurationError("Only path/query parameters are supported.")
            key = (location, name)
            if key in seen:
                raise ExternalConfigurationError("Duplicate OpenAPI parameter.")
            seen.add(key)
            params[key] = parameter
    for (location, name), parameter in params.items():
        schema = resolve_local_ref(parameter.get("schema"), document)
        if not isinstance(schema, dict) or schema.get("type") not in {
            "string",
            "number",
            "integer",
            "boolean",
        }:
            raise ExternalConfigurationError("Path/query parameters must have primitive schemas.")
        expected_style = "simple" if location == "path" else "form"
        if parameter.get("style", expected_style) != expected_style or parameter.get(
            "allowReserved"
        ):
            raise ExternalConfigurationError("Unsupported parameter serialization.")
        if location == "path" and parameter.get("required") is not True:
            raise ExternalConfigurationError("Path parameters must be required.")
        group = groups.setdefault(
            location,
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        )
        group["properties"][name] = schema
        if parameter.get("required"):
            group["required"].append(name)
    path_parameters = set(groups.get("path", {}).get("properties", {}))
    if set(_PLACEHOLDER.findall(path)) != path_parameters or "{" in _PLACEHOLDER.sub("", path):
        raise ExternalConfigurationError("Path template and parameters do not match.")
    required = [name for name, schema in groups.items() if schema["required"]]
    if "requestBody" in operation:
        body = resolve_local_ref(operation["requestBody"], document)
        if not isinstance(body, dict):
            raise ExternalConfigurationError("Invalid OpenAPI request body.")
        content = body.get("content", {})
        if not isinstance(content, dict) or set(content) != {"application/json"}:
            raise ExternalConfigurationError("Only application/json request bodies are supported.")
        media = content["application/json"]
        if not isinstance(media, dict) or "schema" not in media:
            raise ExternalConfigurationError("JSON request body requires a schema.")
        groups["body"] = resolve_local_ref(media["schema"], document)
        if body.get("required"):
            required.append("body")
    return sanitize_schema(
        {
            "type": "object",
            "properties": groups,
            "required": required,
            "additionalProperties": False,
        },
        root=document,
    )
