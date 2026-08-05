from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from kernel_rag import (
    LocalObjectStore,
    ObjectStoreError,
    ObjectTooLargeError,
    S3ObjectStore,
    bucket_and_key_from_s3_uri,
    create_object_store,
)


def test_local_object_store_writes_document_with_safe_key(tmp_path: Path) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    knowledge_base_id = UUID("00000000-0000-0000-0000-000000000001")

    stored = store.write_document(
        knowledge_base_id=knowledge_base_id,
        filename="../Deploy Guide.md",
        content=b"# Deploy\n",
        content_type="text/markdown",
    )

    assert stored.key.startswith(f"knowledge-bases/{knowledge_base_id}/documents/")
    assert stored.key.endswith("_Deploy_Guide.md")
    assert stored.uri == f"object://local/{stored.key}"
    assert stored.checksum.startswith("sha256:")
    assert stored.size_bytes == 9
    assert stored.content_type == "text/markdown"
    assert store.read_bytes(stored.key) == b"# Deploy\n"


def test_local_object_store_rejects_oversized_objects(tmp_path: Path) -> None:
    store = LocalObjectStore(root_path=tmp_path, max_object_bytes=3)

    with pytest.raises(ObjectTooLargeError):
        store.write_document(
            knowledge_base_id=UUID("00000000-0000-0000-0000-000000000001"),
            filename="too-large.txt",
            content=b"1234",
        )


def test_local_object_store_rejects_unsafe_keys(tmp_path: Path) -> None:
    store = LocalObjectStore(root_path=tmp_path)

    with pytest.raises(ObjectStoreError):
        store.read_bytes("../outside.txt")


def test_create_object_store_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_KERNEL_OBJECT_STORE_BACKEND", raising=False)

    store = create_object_store()

    assert isinstance(store, LocalObjectStore)


def test_create_object_store_rejects_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_KERNEL_OBJECT_STORE_BACKEND", "ftp")

    with pytest.raises(ObjectStoreError, match="AGENT_KERNEL_OBJECT_STORE_BACKEND"):
        create_object_store()


def test_s3_object_store_writes_document_with_safe_key() -> None:
    client = _FakeS3Client()
    store = S3ObjectStore(
        bucket="agent-kernel",
        prefix="tenant-a",
        client=client,
    )
    knowledge_base_id = UUID("00000000-0000-0000-0000-000000000001")

    stored = store.write_document(
        knowledge_base_id=knowledge_base_id,
        filename="../Deploy Guide.md",
        content=b"# Deploy\n",
        content_type="text/markdown",
    )

    assert stored.key.startswith(f"tenant-a/knowledge-bases/{knowledge_base_id}/documents/")
    assert stored.key.endswith("_Deploy_Guide.md")
    assert stored.uri == f"s3://agent-kernel/{stored.key}"
    assert stored.checksum.startswith("sha256:")
    assert stored.size_bytes == 9
    assert stored.content_type == "text/markdown"
    assert client.objects[("agent-kernel", stored.key)] == b"# Deploy\n"
    assert client.puts[0]["ContentType"] == "text/markdown"
    assert client.puts[0]["Metadata"]["sha256"] == stored.checksum.removeprefix("sha256:")
    assert store.read_uri_bytes(stored.uri) == b"# Deploy\n"


def test_s3_object_store_writes_and_reads_artifacts() -> None:
    client = _FakeS3Client()
    store = S3ObjectStore(bucket="agent-kernel", client=client)

    stored = store.write_artifact(
        key="documents/doc-1/parsed/job-1.txt",
        content=b"parsed",
        content_type="text/plain",
    )

    assert stored.key == "documents/doc-1/parsed/job-1.txt"
    assert stored.uri == "s3://agent-kernel/documents/doc-1/parsed/job-1.txt"
    assert store.read_bytes(stored.key) == b"parsed"


def test_s3_object_store_rejects_oversized_objects() -> None:
    store = S3ObjectStore(bucket="agent-kernel", client=_FakeS3Client(), max_object_bytes=3)

    with pytest.raises(ObjectTooLargeError):
        store.write_artifact(key="too-large.txt", content=b"1234")


def test_s3_object_store_rejects_unsafe_keys_and_bucket_mismatch() -> None:
    store = S3ObjectStore(bucket="agent-kernel", client=_FakeS3Client())

    with pytest.raises(ObjectStoreError):
        store.write_artifact(key="../outside.txt", content=b"nope")
    with pytest.raises(ObjectStoreError, match="does not match configured bucket"):
        store.read_uri_bytes("s3://other-bucket/documents/a.txt")


def test_s3_object_store_uri_parser() -> None:
    assert bucket_and_key_from_s3_uri("s3://agent-kernel/documents/a.txt") == (
        "agent-kernel",
        "documents/a.txt",
    )

    with pytest.raises(ObjectStoreError):
        bucket_and_key_from_s3_uri("object://local/documents/a.txt")
    with pytest.raises(ObjectStoreError):
        bucket_and_key_from_s3_uri("s3://agent-kernel")


def test_create_object_store_selects_s3_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_KERNEL_OBJECT_STORE_BACKEND", "s3")
    monkeypatch.setenv("AGENT_KERNEL_S3_BUCKET", "agent-kernel")

    created_clients: list[dict[str, str | None]] = []

    def fake_create_s3_client(*, endpoint_url: str | None, region_name: str | None) -> Any:
        created_clients.append({"endpoint_url": endpoint_url, "region_name": region_name})
        return _FakeS3Client()

    monkeypatch.setattr("kernel_rag.object_store._create_s3_client", fake_create_s3_client)

    store = create_object_store()

    assert isinstance(store, S3ObjectStore)
    assert store.bucket == "agent-kernel"
    assert created_clients == [{"endpoint_url": None, "region_name": None}]


class _FakeS3Body:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.puts: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        body = kwargs["Body"]
        assert isinstance(bucket, str)
        assert isinstance(key, str)
        assert isinstance(body, bytes)
        self.objects[(bucket, key)] = body
        self.puts.append(kwargs)

    def get_object(self, **kwargs: Any) -> dict[str, _FakeS3Body]:
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        assert isinstance(bucket, str)
        assert isinstance(key, str)
        return {"Body": _FakeS3Body(self.objects[(bucket, key)])}
