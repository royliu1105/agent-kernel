"""Structured logging helpers for correlation fields."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kernel_observability.tracing import ObservabilityContext


def build_log_fields(
    context: ObservabilityContext,
    *,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    tool_name: str | None = None,
    error_type: str | None = None,
    extra: Mapping[str, str | int | float | bool | None] | None = None,
) -> dict[str, str | int | float | bool]:
    """Build structured log fields without raw prompts, secrets, or payloads."""

    fields: dict[str, str | int | float | bool] = dict(context.to_log_fields())
    _add_if_present(fields, "status", status)
    _add_if_present(fields, "provider", provider)
    _add_if_present(fields, "model", model)
    _add_if_present(fields, "tool_name", tool_name)
    _add_if_present(fields, "error_type", error_type)
    if extra is not None:
        for key, value in extra.items():
            _add_if_present(fields, key, value)
    return fields


def _add_if_present(
    fields: dict[str, str | int | float | bool],
    key: str,
    value: Any,
) -> None:
    if value is not None:
        fields[key] = value
