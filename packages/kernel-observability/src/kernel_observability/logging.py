"""Structured logging helpers for correlation fields."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from kernel_observability.redaction import redact_fields, safe_event_name, safe_identifier
from kernel_observability.tracing import ObservabilityContext

LogScalar = str | int | float | bool
LogFieldValue = LogScalar | None


def build_log_fields(
    context: ObservabilityContext,
    *,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    tool_name: str | None = None,
    error_type: str | None = None,
    extra: Mapping[str, LogFieldValue] | None = None,
) -> dict[str, LogScalar]:
    """Build structured log fields without raw prompts, secrets, or payloads."""

    fields: dict[str, LogFieldValue] = dict(context.to_log_fields())
    _add_if_present(fields, "status", status)
    _add_if_present(fields, "provider", provider)
    _add_if_present(fields, "model", model)
    _add_if_present(fields, "tool_name", tool_name)
    _add_if_present(fields, "error_type", error_type)
    if extra is not None:
        for key, value in extra.items():
            _add_if_present(fields, key, value)
    return redact_log_fields(fields)


def build_log_record(
    *,
    event: str,
    context: ObservabilityContext,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    tool_name: str | None = None,
    error_type: str | None = None,
    extra: Mapping[str, LogFieldValue] | None = None,
) -> dict[str, LogScalar]:
    """Build one structured log record."""

    fields = build_log_fields(
        context,
        status=status,
        provider=provider,
        model=model,
        tool_name=tool_name,
        error_type=error_type,
        extra=extra,
    )
    return {**fields, "event": safe_event_name(event)}


def redact_log_fields(fields: Mapping[str, object]) -> dict[str, LogScalar]:
    """Return log fields with sensitive values redacted and ``None`` omitted."""

    return redact_fields(fields)


def log_event(
    logger: logging.Logger,
    *,
    level: int,
    event: str,
    context: ObservabilityContext,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    tool_name: str | None = None,
    error_type: str | None = None,
    extra: Mapping[str, LogFieldValue] | None = None,
) -> None:
    """Emit a structured log event using standard-library logging."""

    record = build_log_record(
        event=event,
        context=context,
        status=status,
        provider=provider,
        model=model,
        tool_name=tool_name,
        error_type=error_type,
        extra=extra,
    )
    logger.log(level, safe_event_name(event), extra={"structured": record})


class JsonLogFormatter(logging.Formatter):
    """Format structured log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        structured = getattr(record, "structured", None)
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": safe_identifier(record.name),
        }
        if isinstance(structured, dict):
            payload.update(redact_log_fields(structured))
        else:
            # Unstructured messages and interpolated arguments may contain any
            # user content. Never render them, including under error handling.
            payload["event"] = "log.unstructured"
        if record.exc_info:
            exception_class = record.exc_info[0]
            payload["exception_type"] = (
                safe_identifier(exception_class.__name__) if exception_class else "unknown"
            )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _add_if_present(
    fields: dict[str, LogFieldValue],
    key: str,
    value: LogFieldValue,
) -> None:
    if value is not None:
        fields[key] = value
