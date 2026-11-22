"""Private, bounded evidence when an external response pin fails.

Unreviewed response bodies must not enter Run output, tool results, or public
logs. Operators may inspect a local evidence file under an ignored private
directory, then update the pin or reject the change.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_DEFAULT_DIR = Path(".agent-kernel/external-response-review")
_MAX_STORE_BYTES = 32_768
_SAFE_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")


def private_evidence_root() -> Path:
    raw = os.environ.get("AGENT_KERNEL_PRIVATE_EVIDENCE_DIR", "").strip()
    root = Path(raw) if raw else _DEFAULT_DIR
    if not root.is_absolute():
        root = Path.cwd() / root
    return root.resolve()


def save_unreviewed_response(
    *,
    tool_name: str,
    expected_sha256: str,
    body: bytes,
    content_type: str | None = None,
    status_code: int | None = None,
) -> Path:
    """Write a private evidence envelope; never return the raw body to callers."""

    if not _SAFE_NAME.match(tool_name):
        tool_name = "external_tool"
    actual = hashlib.sha256(body).hexdigest()
    root = private_evidence_root()
    root.mkdir(parents=True, exist_ok=True)
    # Owner-only directory when possible (best-effort on all platforms).
    with contextlib.suppress(OSError):
        os.chmod(root, 0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"{stamp}-{tool_name}-{uuid4().hex[:8]}.json"
    stored = body[:_MAX_STORE_BYTES]
    payload = {
        "version": 1,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "tool_name": tool_name,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
        "body_byte_length": len(body),
        "stored_byte_length": len(stored),
        "truncated": len(body) > len(stored),
        "status_code": status_code,
        "content_type": content_type,
        "body_base64": None,
        "body_utf8": None,
    }
    # Prefer UTF-8 text when the slice is valid JSON/text; otherwise base64.
    try:
        payload["body_utf8"] = stored.decode("utf-8")
    except UnicodeDecodeError:
        import base64

        payload["body_base64"] = base64.b64encode(stored).decode("ascii")
    raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(raw, encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)
    return path
