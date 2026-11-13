import json
import logging
from typing import Any, cast

import pytest
from kernel_observability import JsonLogFormatter, ObservabilityContext, build_log_record, log_event
from kernel_observability.redaction import REDACTED, redact_fields


def test_content_credentials_nested_objects_and_wrong_numeric_types_are_redacted() -> None:
    sentinel = "private_user_content"
    fields = {
        "prompt": sentinel,
        "arguments": {"foo": sentinel},
        "output": [sentinel],
        "apiKey": sentinel,
        "Authorization": sentinel,
        "cookie": sentinel,
        "request.body": sentinel,
        "response": sentinel,
        "exception.message": sentinel,
        "input_tokens": sentinel,
        "provider": "Bearer abc123",
        "model": "sk-secret123",
        "total_tokens": 42,
        "latency_ms": 10,
        "trace_id": "a" * 32,
    }
    output = redact_fields(fields)
    assert sentinel not in json.dumps(output)
    assert "abc123" not in json.dumps(output) and "secret123" not in json.dumps(output)
    assert output["total_tokens"] == 42
    assert output["trace_id"] == "a" * 32


def test_raw_formatter_structured_bypass_and_exception_never_emit_content() -> None:
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        __file__,
        0,
        "prompt %s",
        ("sentinel",),
        (ValueError, ValueError("exception-sentinel"), None),
    )
    formatter = JsonLogFormatter()
    output = formatter.format(record)
    assert "sentinel" not in output
    assert json.loads(output)["exception_type"] == "ValueError"
    cast(Any, record).structured = {"prompt": "sentinel", "nested": {"password": "sentinel"}}
    assert "sentinel" not in formatter.format(record)


def test_event_is_sanitized_before_standard_logging(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test.redaction")
    with caplog.at_level(logging.INFO):
        log_event(
            logger,
            level=logging.INFO,
            event="prompt=sentinel",
            context=ObservabilityContext.create(),
        )
    assert "sentinel" not in caplog.text
    assert caplog.records[0].getMessage() == REDACTED
    record = build_log_record(
        event="agent.run.started",
        context=ObservabilityContext.create(),
        extra={"event": "overwrite-secret"},
    )
    assert record["event"] == "agent.run.started"


def test_cyclic_or_explosive_objects_are_not_traversed_or_stringified() -> None:
    class Explosive:
        def __str__(self) -> str:
            raise AssertionError("must not stringify")

    cycle: dict[str, object] = {}
    cycle["self"] = cycle
    assert redact_fields({"payload": cycle, "data": Explosive()}) == {
        "payload": REDACTED,
        "data": REDACTED,
    }
    assert len(redact_fields({f"field{i}": "value" for i in range(1000)})) == 64
