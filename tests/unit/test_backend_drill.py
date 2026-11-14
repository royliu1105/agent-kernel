import importlib.util
import sys
from pathlib import Path

import pytest
from kernel_core import DocumentStatus
from kernel_rag.object_store import LocalObjectStore
from kernel_storage import (
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
    create_session_factory,
)
from sqlalchemy import Engine, text

SPEC = importlib.util.spec_from_file_location(
    "backend_drill", Path(__file__).parents[2] / "scripts" / "backend_drill.py"
)
assert SPEC is not None and SPEC.loader is not None
backend_drill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = backend_drill
SPEC.loader.exec_module(backend_drill)
DrillError = backend_drill.DrillError
_object_path = backend_drill._object_path
build_manifest = backend_drill.build_manifest
require_test_service = backend_drill.require_test_service
verify_manifest = backend_drill.verify_manifest


@pytest.mark.parametrize(
    "backend,url",
    [
        ("postgresql", "postgresql://localhost/production"),
        ("postgresql", "postgresql://db.example/agent_kernel_test"),
        ("redis", "redis://localhost:6379/0"),
        ("redis", "redis://db.example:6379/15"),
    ],
)
def test_rejects_non_test_targets(monkeypatch: pytest.MonkeyPatch, backend: str, url: str) -> None:
    monkeypatch.setenv("AGENT_KERNEL_ALLOW_BACKEND_DRILL", "1")
    with pytest.raises(DrillError):
        require_test_service(url, backend=backend)


def test_requires_explicit_safety_acknowledgment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_KERNEL_ALLOW_BACKEND_DRILL", raising=False)
    with pytest.raises(DrillError, match="disposable"):
        require_test_service("redis://localhost:6379/15", backend="redis")


@pytest.mark.parametrize("key", ["../private", "/private", "a/../b", "a//b"])
def test_manifest_rejects_unsafe_object_keys(tmp_path: Path, key: str) -> None:
    with pytest.raises(DrillError):
        _object_path(tmp_path, f"object://local/{key}")


def test_manifest_detects_object_corruption_missing_bytes_and_database_mismatch(
    tmp_path: Path,
    postgres_engine: Engine,
) -> None:
    engine = postgres_engine
    store = LocalObjectStore(root_path=tmp_path)
    try:
        with create_session_factory(engine)() as session:
            kb = KnowledgeBaseRepository(session).create(name="backup")
            stored = store.write_document(
                knowledge_base_id=kb.id, filename="a.txt", content=b"source"
            )
            document = DocumentRepository(session).create(
                knowledge_base_id=kb.id,
                title="a",
                source_uri=stored.uri,
                checksum=stored.checksum,
                status=DocumentStatus.UPLOADED,
            )
            assert document is not None
            jobs = IngestionJobRepository(session)
            job = jobs.create(document_id=document.id)
            assert job is not None
            jobs.mark_parsing(job_id=job.id, parser_name="drill")
            parsed = store.write_artifact(
                key=f"documents/{document.id}/parsed/{job.id}.txt", content=b"parsed"
            )
            jobs.complete_parsed(
                job_id=job.id,
                parsed_text_uri=parsed.uri,
                parsed_text_checksum=parsed.checksum,
                parsed_text_size_bytes=6,
                content_char_count=6,
            )
        manifest = build_manifest(engine, tmp_path)
        assert len(manifest["objects"]) == 2
        verify_manifest(engine, tmp_path, manifest)
        path = _object_path(tmp_path, parsed.uri)
        path.write_bytes(b"corrupt")
        with pytest.raises(DrillError, match="checksum"):
            verify_manifest(engine, tmp_path, manifest)
        path.unlink()
        with pytest.raises(FileNotFoundError):
            verify_manifest(engine, tmp_path, manifest)
        path.write_bytes(b"parsed")
        with engine.begin() as connection:
            connection.execute(text("UPDATE documents SET title='different backup'"))
        with pytest.raises(DrillError, match="database rows"):
            verify_manifest(engine, tmp_path, manifest)
    finally:
        engine.dispose()
