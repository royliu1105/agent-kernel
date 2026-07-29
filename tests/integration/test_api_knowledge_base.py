from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
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
