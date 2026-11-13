from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_identity import PrincipalType, WorkspaceRole
from kernel_providers import LLMFinishReason, LLMRequest, LLMResponse, LLMToolCall, LLMUsage
from kernel_rag import KnowledgeBaseSearchTool, LocalObjectStore
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService
from kernel_storage import (
    AgentRepository,
    ApiKeyRepository,
    ApprovalRepository,
    KnowledgeBaseRepository,
    PrincipalRepository,
    RunRepository,
    ToolCallRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy.orm import Session, sessionmaker


def _client(
    factory: sessionmaker[Session],
    store: LocalObjectStore,
    role: WorkspaceRole = WorkspaceRole.OPERATOR,
) -> tuple[TestClient, UUID]:
    with factory() as session:
        workspace = WorkspaceRepository(session).create(name="scope", slug=uuid4().hex)
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER, display_name="test operator"
        )
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id, workspace_id=workspace.id, role=role
        )
        key = ApiKeyRepository(session).issue(
            workspace_id=workspace.id, principal_id=principal.id, name="test"
        )
        assert key is not None
    return TestClient(
        create_app(session_factory=factory, object_store=store, api_key_auth_enabled=True),
        headers={"Authorization": f"Bearer {key.plaintext_key}"},
    ), workspace.id


def _indexed_knowledge(client: TestClient, name: str) -> dict[str, str]:
    response = client.post("/v1/knowledge-bases", json={"name": name})
    assert response.status_code == 201, response.text
    kb = response.json()["id"]
    response = client.post(
        f"/v1/knowledge-bases/{kb}/documents/upload",
        files={
            "file": ("guide.md", f"private {name} deployment checklist".encode(), "text/markdown")
        },
    )
    assert response.status_code == 201, response.text
    doc = response.json()["id"]
    source = response.json()["source_uri"]
    response = client.post(f"/v1/documents/{doc}/ingest")
    assert response.status_code == 201, response.text
    job = response.json()["id"]
    response = client.post(f"/v1/documents/{doc}/chunk")
    assert response.status_code == 201, response.text
    chunk = response.json()[0]["id"]
    response = client.post(f"/v1/documents/{doc}/index")
    assert response.status_code == 201, response.text
    return {"kb": kb, "doc": doc, "job": job, "chunk": chunk, "source": source}


def test_api_isolates_complete_knowledge_pipeline(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    a, workspace_a = _client(sqlite_session_factory, store)
    b, _ = _client(sqlite_session_factory, store)
    own = _indexed_knowledge(a, "a")
    foreign = _indexed_knowledge(b, "b")
    with sqlite_session_factory() as session:
        legacy = KnowledgeBaseRepository(session).create(name="legacy")

    assert [kb["id"] for kb in a.get("/v1/knowledge-bases").json()] == [own["kb"]]
    assert a.get(f"/v1/knowledge-bases/{own['kb']}").json()["workspace_id"] == str(workspace_a)
    assert a.get(f"/v1/knowledge-bases/{legacy.id}").status_code == 404
    result = a.post(f"/v1/knowledge-bases/{own['kb']}/retrieve", json={"query": "deployment"})
    assert result.status_code == 200
    assert result.json()["results"][0]["citation"]["document_id"] == own["doc"]

    reads, writes = (
        Mock(side_effect=AssertionError("unexpected object read")),
        Mock(side_effect=AssertionError("unexpected object write")),
    )
    monkeypatch.setattr(store, "read_uri_bytes", reads)
    monkeypatch.setattr(store, "write_document", writes)
    from kernel_rag.embeddings import MockEmbeddingProvider

    embeds = Mock(side_effect=AssertionError("unexpected embedding call"))
    monkeypatch.setattr(MockEmbeddingProvider, "embed_texts", embeds)

    for caller, denied in [(a, foreign), (b, own)]:
        for method, template, payload in [
            ("GET", "/v1/knowledge-bases/{kb}", None),
            ("GET", "/v1/knowledge-bases/{kb}/documents", None),
            ("POST", "/v1/knowledge-bases/{kb}/documents", {"title": "x", "source_uri": "x"}),
            ("POST", "/v1/knowledge-bases/{kb}/retrieve", {"query": "private"}),
            ("GET", "/v1/documents/{doc}", None),
            ("POST", "/v1/documents/{doc}/ingest", None),
            ("POST", "/v1/documents/{doc}/chunk", None),
            ("POST", "/v1/documents/{doc}/index", None),
            ("GET", "/v1/documents/{doc}/chunks", None),
            ("GET", "/v1/documents/{doc}/embeddings", None),
            ("GET", "/v1/documents/{doc}/ingestion-jobs", None),
            ("GET", "/v1/document-chunks/{chunk}", None),
            ("GET", "/v1/ingestion-jobs/{job}", None),
        ]:
            response = caller.request(method, template.format(**denied), json=payload)
            missing = caller.request(
                method, template.format(**{key: str(uuid4()) for key in denied}), json=payload
            )
            assert response.status_code == missing.status_code == 404, response.text
            assert "private" not in response.text
        assert (
            caller.post(
                f"/v1/knowledge-bases/{denied['kb']}/documents/upload",
                files={"file": ("x.txt", b"forged", "text/plain")},
            ).status_code
            == 404
        )

    forged = a.post(
        f"/v1/knowledge-bases/{own['kb']}/documents",
        json={"title": "forged", "source_uri": foreign["source"]},
    )
    assert forged.status_code == 422
    assert foreign["source"] not in forged.text
    reads.assert_not_called()
    writes.assert_not_called()
    embeds.assert_not_called()


def test_knowledge_role_denial_is_separate_from_scope(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    viewer, workspace = _client(sqlite_session_factory, store, WorkspaceRole.VIEWER)
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session, workspace_id=workspace).create(name="visible")
    assert viewer.get(f"/v1/knowledge-bases/{kb.id}").status_code == 200
    assert viewer.post("/v1/knowledge-bases", json={"name": "denied"}).status_code == 403
    assert (
        viewer.post(
            f"/v1/knowledge-bases/{kb.id}/documents/upload",
            files={"file": ("x.txt", b"no", "text/plain")},
        ).status_code
        == 403
    )
    assert not list(tmp_path.iterdir())


class _SearchProvider:
    name = "native"

    def __init__(self, arguments: dict[str, Any]) -> None:
        self.arguments = arguments
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="" if len(self.requests) == 1 else "done",
            usage=LLMUsage(input_tokens=1, output_tokens=1, estimated_cost=0),
            finish_reason=LLMFinishReason.TOOL_CALLS
            if len(self.requests) == 1
            else LLMFinishReason.STOP,
            tool_calls=(LLMToolCall(id="call1", name="kb_search", arguments=self.arguments),)
            if len(self.requests) == 1
            else (),
        )


class _ApprovalSearchTool(KnowledgeBaseSearchTool):
    @property
    def metadata(self) -> ToolMetadata:
        return super().metadata.model_copy(update={"risk_level": RiskLevel.EXTERNAL_WRITE})


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True], ids=["explicit", "native"])
@pytest.mark.parametrize("path", ["inline", "worker", "resume"])
@pytest.mark.parametrize("foreign", [False, True], ids=["own", "foreign"])
async def test_runtime_knowledge_scope_comes_from_persisted_run(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
    native: bool,
    path: str,
    foreign: bool,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    a, workspace_a = _client(sqlite_session_factory, store)
    b, workspace_b = _client(sqlite_session_factory, store)
    target = _indexed_knowledge(b if foreign else a, "secret")
    arguments = {"knowledge_base_id": target["kb"], "query": "deployment"}
    provider = _SearchProvider(arguments)
    registry = ToolRegistry()
    tool_type = _ApprovalSearchTool if path == "resume" else KnowledgeBaseSearchTool
    registry.register(tool_type(session_factory=sqlite_session_factory))

    def service() -> RunExecutionService:
        return RunExecutionService(router=ModelRouter({"native": provider}), tool_registry=registry)

    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="agent", workspace_id=workspace_a)
        repository = RunRepository(session)
        run = repository.create(
            agent_id=agent.id,
            workspace_id=workspace_a,
            input_payload={
                **(
                    {"task": "search", "model": "native:test"}
                    if native
                    else {"tool": {"name": "kb_search", "arguments": arguments}}
                ),
                "workspace_id": str(workspace_b),
            },
        )
        repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={},
        )
        if path == "worker":
            await QueuedRunWorker(
                session_factory=sqlite_session_factory, execution_service=service()
            ).run_once()
            session.expire_all()
        else:
            await service().execute(run_id=run.id, repository=repository)
        if path == "resume":
            approvals = ApprovalRepository(session)
            approval = approvals.list_for_run(run.id)[0]
            approvals.approve(approval_id=approval.id, decision_note="test")
            # A new service proves context is rebuilt from persistence after interruption.
            await service().resume(
                run_id=run.id,
                repository=repository,
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
                approval_id=approval.id,
            )
        completed = repository.get(run.id)
        calls = ToolCallRepository(session).list_for_run(run.id)
        assert completed is not None
        assert completed.status is (RunStatus.FAILED if foreign else RunStatus.SUCCEEDED)
        assert len(calls) == 1
        if foreign:
            assert calls[0].result is None
            assert completed.error_type == "knowledge_base_not_found"
            assert RunEventType.TOOL_CALL_RETRYING not in {
                event.type for event in repository.list_events(run.id)
            }
            assert "private secret" not in str(completed.model_dump())
            assert len(provider.requests) == (1 if native else 0)
        else:
            assert calls[0].result is not None
            assert calls[0].result["results"][0]["citation"]["document_id"] == target["doc"]
