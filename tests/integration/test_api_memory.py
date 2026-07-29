from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


def test_memory_api_creates_lists_inspects_and_deletes_memory(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    create_response = client.post(
        "/v1/memory",
        json={
            "type": "user_preference",
            "scope": "user:roy",
            "content": {"language": "zh"},
            "confidence": 0.9,
            "metadata": {"source": "manual"},
        },
    )

    assert create_response.status_code == 201
    memory = create_response.json()
    assert memory["type"] == "user_preference"
    assert memory["scope"] == "user:roy"
    assert memory["content"] == {"language": "zh"}
    assert memory["confidence"] == 0.9
    assert memory["metadata"] == {"source": "manual"}

    list_response = client.get("/v1/memory?scope=user%3Aroy&type=user_preference")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [memory["id"]]

    inspect_response = client.get(f"/v1/memory/{memory['id']}")
    assert inspect_response.status_code == 200
    assert inspect_response.json()["id"] == memory["id"]

    delete_response = client.delete(f"/v1/memory/{memory['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"id": memory["id"], "deleted": True}

    inspect_deleted_response = client.get(f"/v1/memory/{memory['id']}")
    assert inspect_deleted_response.status_code == 404


def test_memory_api_filters_by_type_and_limit(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    client.post(
        "/v1/memory",
        json={
            "type": "user_preference",
            "scope": "user:roy",
            "content": {"language": "zh"},
        },
    )
    client.post(
        "/v1/memory",
        json={
            "type": "task_context",
            "scope": "task:deploy",
            "content": {"summary": "Deploy needs approval."},
        },
    )

    list_response = client.get("/v1/memory?type=task_context&limit=1")

    assert list_response.status_code == 200
    memories = list_response.json()
    assert len(memories) == 1
    assert memories[0]["type"] == "task_context"


def test_memory_api_returns_404_for_missing_memory(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    inspect_response = client.get(f"/v1/memory/{missing_id}")
    delete_response = client.delete(f"/v1/memory/{missing_id}")

    assert inspect_response.status_code == 404
    assert delete_response.status_code == 404
