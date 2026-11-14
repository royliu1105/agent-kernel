"""Invalid memory inputs must produce safe client errors without database access."""

from uuid import uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "-Infinity", '"\\ud800"', '"' + "x" * 17000 + '"'],
    ids=["nan", "positive-infinity", "negative-infinity", "surrogate", "oversized"],
)
@pytest.mark.parametrize("field", ["content", "metadata"])
def test_memory_validation_error_is_safe_json(value: str, field: str) -> None:
    other = ',"content":{}' if field == "metadata" else ""
    body = (
        '{"type":"long_term","scope":"shared","'
        + field
        + '":{"private":"do-not-reflect-memory","value":'
        + value
        + "}"
        + other
        + "}"
    )
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/memory", content=body, headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    errors = response.json()["detail"]
    assert errors and errors[0]["loc"][:2] == ["body", field]
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)
    assert "do-not-reflect-memory" not in response.text
    assert len(response.content) < 1000


def test_invalid_selection_and_malformed_json_remain_client_errors() -> None:
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        selection = client.post(
            f"/v1/agents/{uuid4()}/runs",
            content='{"input":{"memory":{"scopes":["shared"],"limit":NaN}}}',
            headers={"Content-Type": "application/json"},
        )
        malformed = client.post(
            "/v1/memory", content='{"content":', headers={"Content-Type": "application/json"}
        )
    assert selection.status_code == malformed.status_code == 422
    assert malformed.json()["detail"][0]["type"] == "json_invalid"
