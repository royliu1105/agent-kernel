"""Structured logging helpers for correlation fields."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from io import TextIOWrapper
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, cast

from kernel_observability.redaction import redact_fields, safe_event_name, safe_identifier
from kernel_observability.tracing import ObservabilityContext

LogScalar = str | int | float | bool
LogFieldValue = LogScalar | None


def uvicorn_log_config() -> dict[str, Any]:
    """Prevent Uvicorn from reinstalling raw access/exception formatters."""
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"safe": {"()": JsonLogFormatter}},
        "handlers": {
            "safe": {
                "class": "logging.StreamHandler",
                "formatter": "safe",
                "stream": "ext://sys.stderr",
            }
        },
        "root": {"handlers": ["safe"], "level": "INFO"},
        "loggers": {
            name: {"handlers": [], "level": "INFO", "propagate": True}
            for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
        },
    }
    if os.getenv("AGENT_KERNEL_LOG_FILE"):
        config["handlers"]["agent_kernel_file"] = {
            "()": create_file_log_handler,
            "formatter": "safe",
        }
        config["root"]["handlers"].append("agent_kernel_file")
    return config


def configure_safe_logging() -> None:
    """Install fail-closed formatting for application and SDK logging sinks.

    Preserve embedding applications' destinations, but never preserve a raw
    formatter: SDK warnings can contain whole provider responses or SQL binds.
    Call before client creation and again at the process entry point.
    """
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    file_path = os.getenv("AGENT_KERNEL_LOG_FILE")
    owned = [handler for handler in root.handlers if handler.name == "agent_kernel_file"]
    if file_path and not owned:
        file_handler = create_file_log_handler()
        file_handler.name = "agent_kernel_file"
        root.addHandler(file_handler)
    formatter = JsonLogFormatter()
    loggers = [root] + [
        logger
        for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger)
    ]
    for logger in loggers:
        for handler in logger.handlers:
            handler.setFormatter(formatter)
    if logging.lastResort is not None:
        logging.lastResort.setFormatter(formatter)
    root.setLevel(logging.INFO)
    logging.captureWarnings(True)
    logging.raiseExceptions = False


class PrivateRotatingFileHandler(RotatingFileHandler):
    """Keep newly opened/rotated files private; the collector uses a read-only mount."""

    def _open(self) -> TextIOWrapper:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
        descriptor = os.open(self.baseFilename, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            return cast(
                TextIOWrapper,
                os.fdopen(descriptor, self.mode, encoding=self.encoding, errors=self.errors),
            )
        except BaseException:
            os.close(descriptor)
            raise


def create_file_log_handler() -> RotatingFileHandler:
    """Build the optional bounded sink without changing the default stderr path."""
    path = Path(os.environ["AGENT_KERNEL_LOG_FILE"])
    if not path.is_absolute():
        raise ValueError("AGENT_KERNEL_LOG_FILE must be an absolute path.")
    try:
        max_bytes = int(os.getenv("AGENT_KERNEL_LOG_MAX_BYTES", "10485760"))
        backups = int(os.getenv("AGENT_KERNEL_LOG_BACKUP_COUNT", "5"))
    except ValueError:
        raise ValueError("Log rotation limits must be integers.") from None
    if not 1024 <= max_bytes <= 104857600 or not 1 <= backups <= 20:
        raise ValueError("Log rotation limits are outside the supported bounds.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handler = PrivateRotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
    )
    handler.setFormatter(JsonLogFormatter())
    return handler


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
