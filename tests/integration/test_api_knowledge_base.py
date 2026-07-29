from pathlib import Path

from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_rag import LocalObjectStore
from sqlalchemy.orm import Session, sessionmaker


def test_knowledge_base_and_document_metadata_api(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    create_kb_response = client.post(
        "/v1/knowledge-bases",
        json={
            "name": "engineering-handbook",
            "description": "Engineering docs",
            "metadata": {"owner": "platform"},
        },
    )
    assert create_kb_response.status_code == 201
    knowledge_base = create_kb_response.json()
    assert knowledge_base["name"] == "engineering-handbook"
    assert knowledge_base["status"] == "active"

    list_kb_response = client.get("/v1/knowledge-bases")
    assert list_kb_response.status_code == 200
    assert [item["id"] for item in list_kb_response.json()] == [knowledge_base["id"]]

    get_kb_response = client.get(f"/v1/knowledge-bases/{knowledge_base['id']}")
    assert get_kb_response.status_code == 200
    assert get_kb_response.json()["metadata"] == {"owner": "platform"}

    create_doc_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents",
        json={
            "title": "Deployment Guide",
            "source_uri": "object://local/docs/deployment.md",
            "mime_type": "text/markdown",
            "checksum": "sha256:abc",
            "size_bytes": 1234,
            "metadata": {"source": "manual"},
        },
    )
    assert create_doc_response.status_code == 201
    document = create_doc_response.json()
    assert document["knowledge_base_id"] == knowledge_base["id"]
    assert document["status"] == "registered"

    list_docs_response = client.get(f"/v1/knowledge-bases/{knowledge_base['id']}/documents")
    assert list_docs_response.status_code == 200
    assert [item["id"] for item in list_docs_response.json()] == [document["id"]]

    get_doc_response = client.get(f"/v1/documents/{document['id']}")
    assert get_doc_response.status_code == 200
    assert get_doc_response.json()["source_uri"] == "object://local/docs/deployment.md"


def test_knowledge_base_document_api_returns_404_for_missing_records(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    get_kb_response = client.get(f"/v1/knowledge-bases/{missing_id}")
    create_doc_response = client.post(
        f"/v1/knowledge-bases/{missing_id}/documents",
        json={"title": "Missing", "source_uri": "object://local/missing.md"},
    )
    list_docs_response = client.get(f"/v1/knowledge-bases/{missing_id}/documents")
    get_doc_response = client.get(f"/v1/documents/{missing_id}")

    assert get_kb_response.status_code == 404
    assert create_doc_response.status_code == 404
    assert list_docs_response.status_code == 404
    assert get_doc_response.status_code == 404


def test_document_upload_api_stores_file_and_metadata(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post(
        "/v1/knowledge-bases",
        json={"name": "engineering-handbook"},
    ).json()

    upload_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        data={"title": "Deploy Guide", "metadata": '{"source":"manual"}'},
        files={"file": ("deploy.md", b"# Deploy\n", "text/markdown")},
    )

    assert upload_response.status_code == 201
    document = upload_response.json()
    assert document["title"] == "Deploy Guide"
    assert document["status"] == "uploaded"
    assert document["mime_type"] == "text/markdown"
    assert document["checksum"].startswith("sha256:")
    assert document["size_bytes"] == 9
    assert document["source_uri"].startswith("object://local/knowledge-bases/")
    assert document["metadata"]["original_filename"] == "deploy.md"
    assert document["metadata"]["source"] == "manual"
    assert object_store.read_bytes(document["metadata"]["object_key"]) == b"# Deploy\n"


def test_document_upload_api_rejects_oversized_file(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path, max_object_bytes=3)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()

    upload_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("too-large.txt", b"1234", "text/plain")},
    )

    assert upload_response.status_code == 413


def test_document_upload_api_returns_404_for_missing_knowledge_base(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    missing_id = "00000000-0000-0000-0000-000000000000"

    upload_response = client.post(
        f"/v1/knowledge-bases/{missing_id}/documents/upload",
        files={"file": ("missing.md", b"# Missing\n", "text/markdown")},
    )

    assert upload_response.status_code == 404
    assert not any(tmp_path.iterdir())


def test_document_ingest_api_parses_uploaded_text_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("deploy.md", b"# Deploy\r\nShip carefully.\n", "text/markdown")},
    ).json()

    ingest_response = client.post(f"/v1/documents/{document['id']}/ingest")

    assert ingest_response.status_code == 201
    job = ingest_response.json()
    assert job["document_id"] == document["id"]
    assert job["status"] == "parsed"
    assert job["parser_name"] == "text-markdown"
    assert job["parsed_text_uri"].startswith("object://local/documents/")
    assert job["parsed_text_checksum"].startswith("sha256:")
    assert job["parsed_text_size_bytes"] == len(b"# Deploy\nShip carefully.\n")
    assert job["content_char_count"] == len("# Deploy\nShip carefully.\n")
    parsed_key = job["parsed_text_uri"].removeprefix("object://local/")
    assert object_store.read_bytes(parsed_key) == b"# Deploy\nShip carefully.\n"

    document_response = client.get(f"/v1/documents/{document['id']}")
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "parsed"

    list_jobs_response = client.get(f"/v1/documents/{document['id']}/ingestion-jobs")
    assert list_jobs_response.status_code == 200
    assert [item["id"] for item in list_jobs_response.json()] == [job["id"]]

    get_job_response = client.get(f"/v1/ingestion-jobs/{job['id']}")
    assert get_job_response.status_code == 200
    assert get_job_response.json()["id"] == job["id"]


def test_document_ingest_api_records_failed_job_for_unsupported_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("paper.pdf", b"%PDF", "application/pdf")},
    ).json()

    ingest_response = client.post(f"/v1/documents/{document['id']}/ingest")

    assert ingest_response.status_code == 201
    job = ingest_response.json()
    assert job["status"] == "failed"
    assert job["error_type"] == "unsupported_document"
    assert "Only text/plain and text/markdown" in job["error_message"]

    document_response = client.get(f"/v1/documents/{document['id']}")
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "failed"


def test_document_ingest_api_rejects_document_that_is_not_uploaded(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents",
        json={"title": "Registered", "source_uri": "object://local/source.md"},
    ).json()

    ingest_response = client.post(f"/v1/documents/{document['id']}/ingest")

    assert ingest_response.status_code == 409


def test_ingestion_job_api_returns_404_for_missing_records(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    ingest_response = client.post(f"/v1/documents/{missing_id}/ingest")
    list_response = client.get(f"/v1/documents/{missing_id}/ingestion-jobs")
    inspect_response = client.get(f"/v1/ingestion-jobs/{missing_id}")

    assert ingest_response.status_code == 404
    assert list_response.status_code == 404
    assert inspect_response.status_code == 404


def test_document_chunk_api_chunks_parsed_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={
            "file": (
                "deploy.md",
                b"alpha beta gamma delta epsilon zeta eta theta iota kappa",
                "text/markdown",
            )
        },
    ).json()
    ingest_response = client.post(f"/v1/documents/{document['id']}/ingest")
    assert ingest_response.status_code == 201

    chunk_response = client.post(f"/v1/documents/{document['id']}/chunk")

    assert chunk_response.status_code == 201
    chunks = chunk_response.json()
    assert len(chunks) == 1
    assert chunks[0]["index"] == 0
    assert chunks[0]["document_id"] == document["id"]
    assert chunks[0]["content"].startswith("alpha beta")
    assert chunks[0]["checksum"].startswith("sha256:")
    assert chunks[0]["token_count_estimate"] >= 1

    document_response = client.get(f"/v1/documents/{document['id']}")
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "chunked"

    list_response = client.get(f"/v1/documents/{document['id']}/chunks")
    assert list_response.status_code == 200
    assert [chunk["id"] for chunk in list_response.json()] == [chunks[0]["id"]]

    inspect_response = client.get(f"/v1/document-chunks/{chunks[0]['id']}")
    assert inspect_response.status_code == 200
    assert inspect_response.json()["id"] == chunks[0]["id"]


def test_document_chunk_api_rejects_unparsed_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("deploy.md", b"# Deploy\n", "text/markdown")},
    ).json()

    chunk_response = client.post(f"/v1/documents/{document['id']}/chunk")

    assert chunk_response.status_code == 409


def test_document_chunk_api_returns_404_for_missing_records(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    chunk_response = client.post(f"/v1/documents/{missing_id}/chunk")
    list_response = client.get(f"/v1/documents/{missing_id}/chunks")
    inspect_response = client.get(f"/v1/document-chunks/{missing_id}")

    assert chunk_response.status_code == 404
    assert list_response.status_code == 404
    assert inspect_response.status_code == 404


def test_document_index_api_embeds_chunked_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("deploy.md", b"alpha beta gamma delta", "text/markdown")},
    ).json()
    assert client.post(f"/v1/documents/{document['id']}/ingest").status_code == 201
    assert client.post(f"/v1/documents/{document['id']}/chunk").status_code == 201

    index_response = client.post(f"/v1/documents/{document['id']}/index")

    assert index_response.status_code == 201
    result = index_response.json()
    assert result["document_id"] == document["id"]
    assert result["model"] == "mock-embedding-v1"
    assert result["dimensions"] == 8
    assert result["embedding_count"] == 1

    document_response = client.get(f"/v1/documents/{document['id']}")
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "indexed"

    embeddings_response = client.get(f"/v1/documents/{document['id']}/embeddings")
    assert embeddings_response.status_code == 200
    embeddings = embeddings_response.json()
    assert len(embeddings) == 1
    assert embeddings[0]["model"] == "mock-embedding-v1"
    assert embeddings[0]["dimensions"] == 8
    assert len(embeddings[0]["vector"]) == 8
    assert embeddings[0]["checksum"].startswith("sha256:")


def test_knowledge_base_retrieve_api_returns_cited_results(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        data={"title": "Deploy Guide"},
        files={
            "file": (
                "deploy.md",
                b"alpha deployment rollback checklist",
                "text/markdown",
            )
        },
    ).json()
    assert client.post(f"/v1/documents/{document['id']}/ingest").status_code == 201
    chunks = client.post(f"/v1/documents/{document['id']}/chunk").json()
    assert client.post(f"/v1/documents/{document['id']}/index").status_code == 201

    retrieve_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/retrieve",
        json={"query": "alpha deployment rollback checklist", "top_k": 1},
    )

    assert retrieve_response.status_code == 200
    payload = retrieve_response.json()
    assert payload["knowledge_base_id"] == knowledge_base["id"]
    assert payload["query"] == "alpha deployment rollback checklist"
    assert payload["model"] == "mock-embedding-v1"
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["content"] == "alpha deployment rollback checklist"
    assert result["score"] >= 0.99
    assert result["metadata"]["embedding_model"] == "mock-embedding-v1"
    citation = result["citation"]
    assert citation["knowledge_base_id"] == knowledge_base["id"]
    assert citation["document_id"] == document["id"]
    assert citation["document_title"] == "Deploy Guide"
    assert citation["document_source_uri"].startswith("object://local/knowledge-bases/")
    assert citation["chunk_id"] == chunks[0]["id"]
    assert citation["chunk_index"] == 0
    assert citation["start_char"] == 0
    assert citation["end_char"] == len("alpha deployment rollback checklist")


def test_knowledge_base_retrieve_api_returns_empty_results(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "empty"}).json()

    retrieve_response = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/retrieve",
        json={"query": "anything"},
    )

    assert retrieve_response.status_code == 200
    assert retrieve_response.json()["results"] == []


def test_knowledge_base_retrieve_api_returns_404_for_missing_knowledge_base(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    retrieve_response = client.post(
        f"/v1/knowledge-bases/{missing_id}/retrieve",
        json={"query": "anything"},
    )

    assert retrieve_response.status_code == 404


def test_document_index_api_rejects_unchunked_document(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, object_store=object_store)
    )
    knowledge_base = client.post("/v1/knowledge-bases", json={"name": "kb"}).json()
    document = client.post(
        f"/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
        files={"file": ("deploy.md", b"alpha beta", "text/markdown")},
    ).json()

    index_response = client.post(f"/v1/documents/{document['id']}/index")

    assert index_response.status_code == 409


def test_document_index_api_returns_404_for_missing_records(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    index_response = client.post(f"/v1/documents/{missing_id}/index")
    embeddings_response = client.get(f"/v1/documents/{missing_id}/embeddings")

    assert index_response.status_code == 404
    assert embeddings_response.status_code == 404
