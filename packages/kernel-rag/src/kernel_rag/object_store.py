"""Filesystem-backed object storage for document artifacts."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

DEFAULT_OBJECT_STORE_ROOT = ".agent-kernel/objects"
OBJECT_STORE_ROOT_ENV = "AGENT_KERNEL_OBJECT_STORE_ROOT"
OBJECT_STORE_BACKEND_ENV = "AGENT_KERNEL_OBJECT_STORE_BACKEND"
S3_BUCKET_ENV = "AGENT_KERNEL_S3_BUCKET"
S3_PREFIX_ENV = "AGENT_KERNEL_S3_PREFIX"
S3_ENDPOINT_URL_ENV = "AGENT_KERNEL_S3_ENDPOINT_URL"
S3_REGION_ENV = "AGENT_KERNEL_S3_REGION"
DEFAULT_MAX_OBJECT_BYTES = 10 * 1024 * 1024
DEFAULT_OBJECT_STORE_BACKEND = "local"
SUPPORTED_OBJECT_STORE_BACKENDS = frozenset({"local", "s3"})


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


LOCAL_OBJECT_URI_PREFIX = "object://local/"
S3_OBJECT_URI_PREFIX = "s3://"


class ObjectStore(Protocol):
    @property
    def max_object_bytes(self) -> int:
        """Maximum accepted object size in bytes."""
        ...

    def write_document(
        self,
        *,
        knowledge_base_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """Persist source document bytes and return object metadata."""
        ...

    def write_artifact(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """Persist generated artifact bytes and return object metadata."""
        ...

    def read_bytes(self, key: str) -> bytes:
        """Read object bytes by backend-local key."""
        ...

    def read_uri_bytes(self, uri: str) -> bytes:
        """Read object bytes by object URI."""
        ...


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
            uri=f"{LOCAL_OBJECT_URI_PREFIX}{key}",
            checksum=checksum,
            size_bytes=size_bytes,
            content_type=content_type,
        )

    def write_artifact(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        size_bytes = len(content)
        if size_bytes > self._max_object_bytes:
            raise ObjectTooLargeError(
                f"Object is {size_bytes} bytes, exceeding limit {self._max_object_bytes}."
            )

        object_path = self._path_for_key(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(content)
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        return StoredObject(
            key=key,
            uri=f"{LOCAL_OBJECT_URI_PREFIX}{key}",
            checksum=checksum,
            size_bytes=size_bytes,
            content_type=content_type,
        )

    def read_bytes(self, key: str) -> bytes:
        return self._path_for_key(key).read_bytes()

    def read_uri_bytes(self, uri: str) -> bytes:
        return self.read_bytes(key_from_local_uri(uri))

    def _path_for_key(self, key: str) -> Path:
        if key.startswith("/") or ".." in Path(key).parts:
            raise ObjectStoreError("Object key must be relative and must not contain '..'.")

        root = self._root_path.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ObjectStoreError("Object key escapes the configured object store root.")
        return path


class S3ObjectStore:
    """S3-compatible object store for AWS S3 and MinIO deployments."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        prefix: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        client: Any | None = None,
        max_object_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
    ) -> None:
        self._bucket = _required_bucket(bucket or os.getenv(S3_BUCKET_ENV))
        self._prefix = _safe_prefix(prefix if prefix is not None else os.getenv(S3_PREFIX_ENV, ""))
        self._client = client or _create_s3_client(
            endpoint_url=endpoint_url or os.getenv(S3_ENDPOINT_URL_ENV),
            region_name=region_name or os.getenv(S3_REGION_ENV),
        )
        self._max_object_bytes = max_object_bytes

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

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
        safe_filename = _safe_filename(filename)
        object_id = uuid4().hex
        key = f"knowledge-bases/{knowledge_base_id}/documents/{object_id}_{safe_filename}"
        return self.write_artifact(key=key, content=content, content_type=content_type)

    def write_artifact(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        _validate_relative_key(key)
        size_bytes = len(content)
        if size_bytes > self._max_object_bytes:
            raise ObjectTooLargeError(
                f"Object is {size_bytes} bytes, exceeding limit {self._max_object_bytes}."
            )

        storage_key = _join_key(self._prefix, key)
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        put_kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": storage_key,
            "Body": content,
            "Metadata": {"sha256": checksum.removeprefix("sha256:")},
        }
        if content_type is not None:
            put_kwargs["ContentType"] = content_type
        try:
            self._client.put_object(**put_kwargs)
        except Exception as error:
            raise ObjectStoreError(f"S3 object write failed: {error}") from error

        return StoredObject(
            key=storage_key,
            uri=f"{S3_OBJECT_URI_PREFIX}{self._bucket}/{storage_key}",
            checksum=checksum,
            size_bytes=size_bytes,
            content_type=content_type,
        )

    def read_bytes(self, key: str) -> bytes:
        _validate_relative_key(key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            content = body.read()
        except Exception as error:
            raise ObjectStoreError(f"S3 object read failed: {error}") from error
        if not isinstance(content, bytes):
            raise ObjectStoreError("S3 object body did not return bytes.")
        return content

    def read_uri_bytes(self, uri: str) -> bytes:
        bucket, key = bucket_and_key_from_s3_uri(uri)
        if bucket != self._bucket:
            raise ObjectStoreError(
                f"S3 object URI bucket {bucket!r} does not match configured bucket."
            )
        return self.read_bytes(key)


def create_object_store(
    *,
    backend: str | None = None,
    max_object_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
) -> ObjectStore:
    configured_backend = backend
    if configured_backend is None:
        configured_backend = os.getenv(OBJECT_STORE_BACKEND_ENV, DEFAULT_OBJECT_STORE_BACKEND)
    resolved_backend = configured_backend.strip().lower()
    if resolved_backend == "":
        resolved_backend = DEFAULT_OBJECT_STORE_BACKEND
    if resolved_backend == "local":
        return LocalObjectStore(max_object_bytes=max_object_bytes)
    if resolved_backend == "s3":
        return S3ObjectStore(max_object_bytes=max_object_bytes)
    supported = ", ".join(sorted(SUPPORTED_OBJECT_STORE_BACKENDS))
    raise ObjectStoreError(f"{OBJECT_STORE_BACKEND_ENV} must be one of: {supported}.")


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        return "document"
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return sanitized.strip("._") or "document"


def key_from_local_uri(uri: str) -> str:
    if not uri.startswith(LOCAL_OBJECT_URI_PREFIX):
        raise ObjectStoreError("Only object://local URIs are supported by LocalObjectStore.")
    key = uri.removeprefix(LOCAL_OBJECT_URI_PREFIX)
    if not key:
        raise ObjectStoreError("Object URI is missing a key.")
    return key


def bucket_and_key_from_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith(S3_OBJECT_URI_PREFIX):
        raise ObjectStoreError("Only s3:// URIs are supported by S3ObjectStore.")
    without_scheme = uri.removeprefix(S3_OBJECT_URI_PREFIX)
    bucket, separator, key = without_scheme.partition("/")
    if not bucket or not separator or not key:
        raise ObjectStoreError("S3 object URI must include bucket and key.")
    _validate_relative_key(key)
    return bucket, key


def _required_bucket(bucket: str | None) -> str:
    if bucket is None or bucket.strip() == "":
        raise ObjectStoreError(f"{S3_BUCKET_ENV} is required for S3 object storage.")
    return bucket


def _safe_prefix(prefix: str | None) -> str:
    if prefix is None or prefix.strip() == "":
        return ""
    normalized = prefix.strip().strip("/")
    _validate_relative_key(normalized)
    return normalized


def _join_key(prefix: str, key: str) -> str:
    return f"{prefix}/{key}" if prefix else key


def _validate_relative_key(key: str) -> None:
    if key.startswith("/") or ".." in Path(key).parts or key.strip() == "":
        raise ObjectStoreError("Object key must be relative and must not contain '..'.")


def _create_s3_client(*, endpoint_url: str | None, region_name: str | None) -> Any:
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as error:
        raise ObjectStoreError(
            "S3 object storage requires boto3. Install boto3 in the deployment image "
            "or provide an injected client."
        ) from error

    kwargs: dict[str, Any] = {}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    if region_name:
        kwargs["region_name"] = region_name
    return boto3.client("s3", **kwargs)
