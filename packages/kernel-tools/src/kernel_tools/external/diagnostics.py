"""Keep untrusted SDK diagnostic payloads out of all application log handlers."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_sdk_context: ContextVar[bool] = ContextVar("external_sdk_diagnostics", default=False)


class _SDKDiagnosticFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _sdk_context.get():
            # MCP uses both named loggers and logging.warning on the root logger.
            # Redact before handlers, including handlers without our formatter.
            record.msg = "External SDK diagnostic omitted (untrusted transport data)."
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


_filter = _SDKDiagnosticFilter()


@contextmanager
def sdk_diagnostics_scope() -> Iterator[None]:
    """Child SDK tasks inherit the scope; application tasks retain their logs.

    Retain filters after exit because another session may still be running.
    They are inert outside SDK tasks and do not replace global logging config.
    """
    root = logging.getLogger()
    root.addFilter(_filter)
    # HTTPCore creates some trace loggers lazily. Root handlers cover their
    # propagated records even when the logger did not exist at scope entry.
    for handler in root.handlers:
        handler.addFilter(_filter)
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split(".", 1)[0] in {
            "mcp",
            "httpx",
            "httpcore",
        }:
            logger.addFilter(_filter)
            for handler in logger.handlers:
                handler.addFilter(_filter)
    token = _sdk_context.set(True)
    try:
        yield
    finally:
        _sdk_context.reset(token)
