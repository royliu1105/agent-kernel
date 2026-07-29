from pathlib import Path
from uuid import UUID

import pytest
from kernel_rag import LocalObjectStore, ObjectStoreError, ObjectTooLargeError


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
