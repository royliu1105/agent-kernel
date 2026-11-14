"""Shared admission limits for stored memory and model context."""

from __future__ import annotations

import json
from typing import Any

MEMORY_CONTENT_BYTES = 16 * 1024
MEMORY_METADATA_BYTES = 4 * 1024
MEMORY_CONTEXT_BYTES = 64 * 1024
MEMORY_MAX_ITEMS = 20
MEMORY_MAX_SCOPES = 8
MEMORY_JSON_DEPTH = 16
MEMORY_JSON_NODES = 4096


def bounded_memory_json(
    value: Any,
    *,
    max_bytes: int,
    max_depth: int = MEMORY_JSON_DEPTH,
    max_nodes: int = MEMORY_JSON_NODES,
) -> str:
    """Bound traversal and encoding, including UTF-8 bytes and JSON escaping."""
    nodes = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise ValueError("Memory JSON exceeds structural limits.")
        if isinstance(item, str):
            if len(item) > max_bytes or len(item.encode("utf-8")) > max_bytes:
                raise ValueError("Memory JSON exceeds byte limit.")
        elif isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("Memory JSON keys must be strings.")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise ValueError("Memory must contain JSON values only.")

    visit(value, 0)
    parts: list[str] = []
    size = 0
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for part in encoder.iterencode(value):
        size += len(part.encode("utf-8"))
        if size > max_bytes:
            raise ValueError("Memory JSON exceeds byte limit.")
        parts.append(part)
    return "".join(parts)


def validate_memory_payload(content: dict[str, Any], metadata: dict[str, Any]) -> None:
    bounded_memory_json(content, max_bytes=MEMORY_CONTENT_BYTES)
    bounded_memory_json(metadata, max_bytes=MEMORY_METADATA_BYTES)
