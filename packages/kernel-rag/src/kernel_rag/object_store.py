"""Filesystem-backed object storage for document artifacts."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

DEFAULT_OBJECT_STORE_ROOT = ".agent-kernel/objects"
OBJECT_STORE_ROOT_ENV = "AGENT_KERNEL_OBJECT_STORE_ROOT"
DEFAULT_MAX_OBJECT_BYTES = 10 * 1024 * 1024


class ObjectStoreError(RuntimeError):
    """Raised when object storage cannot safely write an object."""


class ObjectTooLargeError(ObjectStoreError):
    """Raised when an uploaded object exceeds the configured size limit."""


@dataclass(frozen=True)
class StoredObject:
    key: str
    uri: str
    checksum: str
    size_bytes: int
    content_type: str | None


class LocalObjectStore:
    """Local filesystem object store."""

    def __init__(
        self,
        *,
        root_path: str | Path | None = None,
        max_object_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
    ) -> None:
        configured_root: str | Path
        if root_path is None:
            configured_root = os.getenv(OBJECT_STORE_ROOT_ENV, DEFAULT_OBJECT_STORE_ROOT)
        else:
            configured_root = root_path
        self._root_path = Path(configured_root)
        self._max_object_bytes = max_object_bytes

    @property
    def root_path(self) -> Path:
        return self._root_path

    @property
    def max_object_bytes(self) -> int:
        return self._max_object_bytes

    def write_document(
        self,
        *,
        knowledge_base_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        size_bytes = len(content)
        if size_bytes > self._max_object_bytes:
            raise ObjectTooLargeError(
                f"Object is {size_bytes} bytes, exceeding limit {self._max_object_bytes}."
            )

        safe_filename = _safe_filename(filename)
        object_id = uuid4().hex
        key = f"knowledge-bases/{knowledge_base_id}/documents/{object_id}_{safe_filename}"
        object_path = self._path_for_key(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(content)
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"

        return StoredObject(
            key=key,
            uri=f"object://local/{key}",
            checksum=checksum,
            size_bytes=size_bytes,
            content_type=content_type,
        )

    def read_bytes(self, key: str) -> bytes:
        return self._path_for_key(key).read_bytes()

    def _path_for_key(self, key: str) -> Path:
        if key.startswith("/") or ".." in Path(key).parts:
            raise ObjectStoreError("Object key must be relative and must not contain '..'.")

        root = self._root_path.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ObjectStoreError("Object key escapes the configured object store root.")
        return path


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        return "document"
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return sanitized.strip("._") or "document"
