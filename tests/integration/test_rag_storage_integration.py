from typing import Any

from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_rag import S3ObjectStore
from sqlalchemy.orm import Session, sessionmaker


def test_rag_api_round_trip_with_s3_object_store(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    s3_client = _FakeS3Client()
    object_store = S3ObjectStore(
        bucket="agent-kernel",
        prefix="beta/workspace-a",
        client=s3_client,
    )
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )

    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "prod-kb"}).json()
    upload_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        data={"title": "Production Deploy Guide"},
        files={
            "file": (
                "deploy.md",
                b"# Deploy\r\nalpha deployment rollback checklist\n",
                "text/markdown",
            )
        },
    )

    assert upload_response.status_code == 201
    document = upload_response.json()
    assert document["source_uri"].startswith("s3://agent-kernel/beta/workspace-a/")
    assert document["metadata"]["object_key"].startswith(
        f"beta/workspace-a/knowledge-bases/{knowledge_base['id']}/documents/"
    )
    assert object_store.read_uri_bytes(document["source_uri"]) == (
        b"# Deploy\r\nalpha deployment rollback checklist\n"
    )

    ingest_response = client.post(f"/v1/documents/{document['id']}/ingest")

    assert ingest_response.status_code == 201
    ingestion_job = ingest_response.json()
    assert ingestion_job["status"] == "parsed"
    assert ingestion_job["parsed_text_uri"].startswith(
        "s3://agent-kernel/beta/workspace-a/documents/"
    )
    assert object_store.read_uri_bytes(ingestion_job["parsed_text_uri"]) == (
        b"# Deploy\nalpha deployment rollback checklist\n"
    )

    chunk_response = client.post(f"/v1/documents/{document['id']}/chunk")
    assert chunk_response.status_code == 201
    chunks = chunk_response.json()
    assert len(chunks) == 1

    index_response = client.post(f"/v1/documents/{document['id']}/index")
    assert index_response.status_code == 201
    assert index_response.json()["embedding_count"] == 1

    retrieve_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/retrieve",
        json={"query": "alpha deployment rollback checklist", "top_k": 1},
    )

    assert retrieve_response.status_code == 200
    retrieval = retrieve_response.json()
    assert len(retrieval["results"]) == 1
    result = retrieval["results"][0]
    assert "alpha deployment rollback checklist" in result["content"]
    assert result["metadata"]["embedding_model"] == "mock-embedding-v1"
    assert result["citation"]["document_id"] == document["id"]
    assert result["citation"]["document_title"] == "Production Deploy Guide"
    assert result["citation"]["document_source_uri"] == document["source_uri"]
    assert result["citation"]["chunk_id"] == chunks[0]["id"]


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
