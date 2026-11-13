"""Destructive-to-fixtures-only Redis and PostgreSQL/local-object recovery drills."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from kernel_core import ChunkEmbedding, DocumentChunk, DocumentStatus, RunEventType, RunStatus
from kernel_observability import InMemoryMetricsRecorder
from kernel_providers import MockLLMProvider
from kernel_rag.object_store import LocalObjectStore
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService
from kernel_runtime.queue import QueueFullError, QueueUnavailableError
from kernel_runtime.redis_support import RedisSettings, create_redis_client, create_run_queue
from kernel_storage import (
    AgentRepository,
    Base,
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
    RunRepository,
    WorkspaceRepository,
    create_session_factory,
)
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine, make_url

ROOT = Path(__file__).resolve().parents[1]
ALLOW_ENV = "AGENT_KERNEL_ALLOW_BACKEND_DRILL"


class DrillError(RuntimeError):
    """A safety guard or verification failed; never contains connection credentials."""


def require_test_service(url: str, *, backend: str) -> None:
    if os.environ.get(ALLOW_ENV) != "1":
        raise DrillError(f"Set {ALLOW_ENV}=1 only for disposable local test services.")
    try:
        if backend == "postgresql":
            parsed = make_url(url)
            valid = (
                parsed.get_backend_name() == "postgresql"
                and parsed.host in {"localhost", "127.0.0.1", "::1"}
                and parsed.database == "agent_kernel_test"
                and not parsed.query
            )
        else:
            redis_url = urlsplit(url)
            valid = (
                redis_url.scheme in {"redis", "rediss"}
                and redis_url.hostname in {"localhost", "127.0.0.1", "::1"}
                and redis_url.path == "/15"
                and not redis_url.query
                and not redis_url.fragment
            )
    except ValueError:
        valid = False
    if not valid:
        raise DrillError("Use loopback test services: PostgreSQL agent_kernel_test or Redis DB 15.")


def checksum(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def database_snapshot(engine: Engine) -> dict[str, list[str]]:
    """Canonical row content, including IDs, references, native vectors and revision."""
    result: dict[str, list[str]] = {}
    with engine.connect() as connection:
        for table in sorted(inspect(engine).get_table_names()):
            quoted = engine.dialect.identifier_preparer.quote(table)
            rows = connection.execute(text(f"SELECT * FROM {quoted}")).mappings()
            result[table] = sorted(
                json.dumps(dict(row), sort_keys=True, default=str) for row in rows
            )
    return result


def _linked_objects(engine: Engine) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    with engine.connect() as connection:
        for row in connection.execute(
            text("SELECT id, knowledge_base_id, source_uri, checksum FROM documents ORDER BY id")
        ).mappings():
            uri = str(row["source_uri"])
            expected = f"object://local/knowledge-bases/{row['knowledge_base_id']}/documents/"
            if not uri.startswith(expected):
                raise DrillError("Document object does not belong to its knowledge base.")
            links.append(
                {
                    "document_id": row["id"],
                    "kind": "source",
                    "uri": uri,
                    "expected_checksum": row["checksum"],
                }
            )
        for row in connection.execute(
            text(
                "SELECT id, document_id, parsed_text_uri, parsed_text_checksum "
                "FROM ingestion_jobs ORDER BY id"
            )
        ).mappings():
            uri = row["parsed_text_uri"]
            if uri is None:
                continue
            expected = f"object://local/documents/{row['document_id']}/parsed/{row['id']}.txt"
            if uri != expected:
                raise DrillError("Parsed artifact does not belong to its ingestion job.")
            links.append(
                {
                    "document_id": row["document_id"],
                    "job_id": row["id"],
                    "kind": "parsed",
                    "uri": uri,
                    "expected_checksum": row["parsed_text_checksum"],
                }
            )
        orphan_count = connection.scalar(
            text("""
            SELECT count(*) FROM chunk_embeddings e
            LEFT JOIN document_chunks c ON c.id = e.chunk_id
            LEFT JOIN documents d ON d.id = e.document_id
            WHERE c.id IS NULL OR d.id IS NULL OR c.document_id <> e.document_id
        """)
        )
        if orphan_count:
            raise DrillError("Embedding/document/chunk linkage failed.")
    return links


def _object_path(root: Path, uri: str) -> Path:
    prefix = "object://local/"
    if not uri.startswith(prefix):
        raise DrillError("This rehearsal supports local object manifests only.")
    key = uri[len(prefix) :]
    if not key or any(part in {"", ".", ".."} for part in key.split("/")):
        raise DrillError("Noncanonical object key in restore manifest.")
    candidate = root / key
    if not candidate.resolve().is_relative_to(root.resolve()) or candidate.is_symlink():
        raise DrillError("Object key escapes the restore root.")
    return candidate


def build_manifest(engine: Engine, root: Path) -> dict[str, Any]:
    objects = []
    for link in _linked_objects(engine):
        content = _object_path(root, link["uri"]).read_bytes()
        digest = checksum(content)
        if link["expected_checksum"] != digest:
            raise DrillError("Object checksum differs from its database reference.")
        objects.append({**link, "checksum": digest, "size_bytes": len(content)})
    return {"version": 1, "database": database_snapshot(engine), "objects": objects}


def verify_manifest(engine: Engine, root: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("version") != 1 or manifest.get("database") != database_snapshot(engine):
        raise DrillError("Restored database rows differ from the matching backup manifest.")
    actual = build_manifest(engine, root)
    if actual["objects"] != manifest.get("objects"):
        raise DrillError("Restored object checksum, size or document linkage differs.")


@contextmanager
def disposable_databases(url: str) -> Iterator[tuple[URL, URL]]:
    require_test_service(url, backend="postgresql")
    admin = create_engine(url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    names: list[str] = []
    base = make_url(url)
    try:
        with admin.connect() as connection:
            for purpose in ("source", "restore"):
                name = f"agent_kernel_drill_{purpose}_{uuid4().hex}"
                connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
                names.append(name)
        yield base.set(database=names[0]), base.set(database=names[1])
    finally:
        with admin.connect() as connection:
            for name in reversed(names):
                # Only names created by this invocation can reach the destructive path.
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def _pg_tool(tool: str, url: URL, *, dump: Path, container: str | None = None) -> None:
    if not url.database or not url.database.startswith("agent_kernel_drill_"):
        raise DrillError("PostgreSQL tools may target only databases created by this drill.")
    env = dict(os.environ)
    env.update(
        PGHOST=url.host or "127.0.0.1",
        PGPORT=str(url.port or 5432),
        PGUSER=url.username or "postgres",
        PGPASSWORD=url.password or "",
        PGDATABASE=url.database,
    )
    prefix: list[str] = []
    if container:
        if not container.startswith("agent-kernel-drill-"):
            raise DrillError("PostgreSQL tool container must use the agent-kernel-drill- prefix.")
        label = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                '{{ index .Config.Labels "agent-kernel.drill" }}',
                container,
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        if label != "true":
            raise DrillError("PostgreSQL container requires agent-kernel.drill=true label.")
        env.update(PGHOST="127.0.0.1", PGPORT="5432")
        prefix = ["docker", "exec", "-i"]
        for name in ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"):
            prefix.extend(["-e", name])
        prefix.append(container)
    command = [*prefix, tool, "--no-owner", "--no-privileges"]
    if tool == "pg_dump":
        with dump.open("wb") as output:
            subprocess.run(
                [*command, "--format=custom"],
                env=env,
                stdout=output,
                stderr=subprocess.PIPE,
                check=True,
                timeout=120,
            )
    else:
        with dump.open("rb") as source:
            subprocess.run(
                [*command, "--exit-on-error", "--dbname", url.database],
                env=env,
                stdin=source,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                timeout=120,
            )


def _seed_backup_fixture(engine: Engine, root: Path) -> UUID:
    store = LocalObjectStore(root_path=root)
    content = b"Recovery fixture: a document and its matching parsed bytes.\n"
    with create_session_factory(engine)() as session:
        workspace = WorkspaceRepository(session).create(name="drill", slug="drill")
        agent = AgentRepository(session).create(name="restore usage", workspace_id=workspace.id)
        runs = RunRepository(session)
        run = runs.create(agent_id=agent.id, workspace_id=workspace.id, input_payload={})
        runs.record_usage(
            run.id,
            input_tokens=12,
            output_tokens=3,
            estimated_cost=0.125,
            provider="fixture",
            model="restore-model",
        )
        kb = KnowledgeBaseRepository(session, workspace_id=workspace.id).create(name="restore")
        stored = store.write_document(
            knowledge_base_id=kb.id, filename="source.md", content=content
        )
        document = DocumentRepository(session, workspace_id=workspace.id).create(
            knowledge_base_id=kb.id,
            title="restore fixture",
            source_uri=stored.uri,
            checksum=stored.checksum,
            status=DocumentStatus.UPLOADED,
        )
        assert document is not None
        jobs = IngestionJobRepository(session, workspace_id=workspace.id)
        job = jobs.create(document_id=document.id)
        assert job is not None
        jobs.mark_parsing(job_id=job.id, parser_name="backend-drill")
        parsed = store.write_artifact(
            key=f"documents/{document.id}/parsed/{job.id}.txt", content=content
        )
        jobs.complete_parsed(
            job_id=job.id,
            parsed_text_uri=parsed.uri,
            parsed_text_checksum=parsed.checksum,
            parsed_text_size_bytes=parsed.size_bytes,
            content_char_count=len(content),
        )
        chunk = DocumentChunk(
            document_id=document.id,
            index=0,
            content=content.decode(),
            start_char=0,
            end_char=len(content),
            token_count_estimate=12,
            checksum=checksum(content),
        )
        DocumentChunkRepository(session).replace_for_document(
            document_id=document.id, chunks=[chunk]
        )
        ChunkEmbeddingRepository(session, vector_store_mode="pgvector").replace_for_document(
            document_id=document.id,
            model="drill",
            embeddings=[
                ChunkEmbedding(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    model="drill",
                    dimensions=3,
                    vector=[1.0, 0.0, 0.0],
                    checksum=chunk.checksum,
                )
            ],
        )
        return kb.id


def run_backup_drill(url: str, *, pg_container: str | None = None) -> dict[str, Any]:
    with (
        disposable_databases(url) as (source_url, restored_url),
        TemporaryDirectory(prefix="agent-kernel-backup-drill-") as temporary,
    ):
        root = Path(temporary)
        env = {**os.environ, "DATABASE_URL": source_url.render_as_string(hide_password=False)}
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=True,
            timeout=120,
        )
        source = create_engine(source_url)
        restored = create_engine(restored_url)
        try:
            kb_id = _seed_backup_fixture(source, root / "source-objects")
            manifest = build_manifest(source, root / "source-objects")
            dump = root / "database.dump"
            _pg_tool("pg_dump", source_url, dump=dump, container=pg_container)
            manifest["dump_checksum"] = checksum(dump.read_bytes())
            (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
            shutil.copytree(root / "source-objects", root / "backup-objects")
            shutil.copytree(root / "backup-objects", root / "restored-objects")
            saved = json.loads((root / "manifest.json").read_text())
            if checksum(dump.read_bytes()) != saved["dump_checksum"]:
                raise DrillError("Database dump checksum mismatch.")
            _pg_tool("pg_restore", restored_url, dump=dump, container=pg_container)
            verify_manifest(restored, root / "restored-objects", saved)
            with create_session_factory(restored)() as session:
                hits = ChunkEmbeddingRepository(
                    session, vector_store_mode="pgvector"
                ).similarity_search(
                    knowledge_base_id=kb_id, query_vector=[1.0, 0.0, 0.0], model="drill"
                )
                if len(hits) != 1 or abs(hits[0][1] - 1.0) > 0.00001:
                    raise DrillError("Restored pgvector retrieval failed.")
            # Prove the verifier rejects a mismatched artifact, not just a happy-path copy.
            artifact = _object_path(root / "restored-objects", saved["objects"][-1]["uri"])
            artifact.write_bytes(b"corrupt restored artifact")
            try:
                verify_manifest(restored, root / "restored-objects", saved)
            except DrillError:
                corruption_detected = True
            else:
                raise DrillError("Manifest failed to detect artifact corruption.")
            return {
                "passed": True,
                "scenario": "postgresql-local-object-restore",
                "tables_verified": len(saved["database"]),
                "objects_verified": len(saved["objects"]),
                "pgvector_retrieval_verified": True,
                "corruption_detected": corruption_detected,
                "dump_checksum": saved["dump_checksum"],
            }
        finally:
            source.dispose()
            restored.dispose()


async def run_queue_drill(url: str) -> dict[str, Any]:
    require_test_service(url, backend="redis")
    settings = RedisSettings(
        url=url,
        queue_backend="redis",
        queue_name=f"agent-kernel:drill:{uuid4().hex}",
        queue_max_length=2,
    )
    client = create_redis_client(settings)
    queue = create_run_queue(settings, client=client)
    assert queue is not None
    with TemporaryDirectory(prefix="agent-kernel-queue-drill-") as temporary:
        engine = create_engine(f"sqlite:///{temporary}/runs.db")
        Base.metadata.create_all(engine)
        sessions = create_session_factory(engine)
        try:
            with sessions() as session:
                agent = AgentRepository(session).create(name="queue-drill")
                repository = RunRepository(session)
                run_ids = []
                for number in range(3):
                    run = repository.create(
                        agent_id=agent.id,
                        input_payload={"task": f"drill {number}", "model": "mock:drill"},
                    )
                    repository.apply_transition(
                        run_id=run.id,
                        status=RunStatus.QUEUED,
                        event_type=RunEventType.RUN_QUEUED,
                        payload={"from_status": "created", "to_status": "queued"},
                    )
                    run_ids.append(run.id)
            queue.enqueue(run_ids[0])
            queue.enqueue(run_ids[1])
            try:
                queue.enqueue(run_ids[2])
            except QueueFullError:
                full_detected = True
            else:
                raise DrillError("Queue capacity guard failed.")
            client.lpush(settings.queue_name, b"not-a-uuid")
            hints = queue.dequeue(limit=3)
            if hints != tuple(run_ids[:2]) or queue.malformed_items != 1:
                raise DrillError("Malformed queue hint handling failed.")
            # Hints already popped are intentionally lost, as after a worker crash.
            # Destroy only this invocation's key and make it wrong-type to exercise errors.
            client.set(settings.queue_name, "fault-injection")
            try:
                queue.dequeue()
            except QueueUnavailableError:
                outage_detected = True
            else:
                raise DrillError("Queue failure was not surfaced.")
            metrics = InMemoryMetricsRecorder()
            worker = QueuedRunWorker(
                session_factory=sessions,
                run_queue=queue,
                metrics_recorder=metrics,
                execution_service=RunExecutionService(
                    router=ModelRouter({"mock": MockLLMProvider()})
                ),
            )
            await worker.run_once(limit=10)
            fallback_count = metrics.counter_value(
                "run_queue_errors_total", labels={"operation": "dequeue"}
            )
            if fallback_count != 1:
                raise DrillError("Worker did not observe the injected Redis fault.")
            with sessions() as session:
                runs = [RunRepository(session).get(run_id) for run_id in run_ids]
                if any(run is None or run.status is not RunStatus.SUCCEEDED for run in runs):
                    raise DrillError("Database polling did not recover lost/rejected queue hints.")
            return {
                "passed": True,
                "scenario": "redis-hint-loss-database-poll-recovery",
                "runs_recovered": len(run_ids),
                "queue_full_detected": full_detected,
                "queue_error_detected": outage_detected,
                "worker_queue_fallbacks": int(fallback_count),
                "malformed_hints": queue.malformed_items,
                "durable_store": "sqlite-test-fixture",
            }
        finally:
            engine.dispose()
            try:
                client.delete(settings.queue_name)
            finally:
                client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=["queue", "backup"])
    parser.add_argument("--pg-tools-container", help="Disposable labeled PostgreSQL tool container")
    args = parser.parse_args()
    try:
        if args.scenario == "queue":
            report = asyncio.run(run_queue_drill(os.environ.get("AGENT_KERNEL_TEST_REDIS_URL", "")))
        else:
            report = run_backup_drill(
                os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL", ""),
                pg_container=args.pg_tools_container,
            )
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except Exception as error:
        # Driver/subprocess errors can contain URLs and secrets. Report only safe categories.
        print(
            json.dumps(
                {
                    "passed": False,
                    "error_type": type(error).__name__,
                    "detail": str(error)
                    if isinstance(error, DrillError)
                    else "Backend drill failed.",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
