"""Blocking retrieval must not starve tool deadlines or execution ownership."""

import asyncio
import time
from threading import Event
from typing import Any

import pytest
from kernel_core import RunEventType, RunStatus
from kernel_rag import KnowledgeBaseSearchTool, Retriever
from kernel_rag.retrieval import RetrievalResponse
from kernel_runtime import RunExecutionService
from kernel_storage import AgentRepository, KnowledgeBaseRepository, RunRepository
from kernel_tools import ToolExecutor, ToolMetadata, ToolRegistry, ToolRequest, ToolTimeoutError
from sqlalchemy.orm import Session, sessionmaker


class BlockingRetriever(Retriever):
    def __init__(self, seconds: float) -> None:
        super().__init__()
        self.seconds = seconds
        self.finished = Event()

    def retrieve(self, **kwargs: Any) -> RetrievalResponse:
        try:
            time.sleep(self.seconds)
            return super().retrieve(**kwargs)
        finally:
            self.finished.set()


class ShortDeadlineSearch(KnowledgeBaseSearchTool):
    @property
    def metadata(self) -> ToolMetadata:
        return super().metadata.model_copy(update={"timeout_ms": 30})


@pytest.mark.asyncio
async def test_blocking_search_obeys_tool_deadline(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="deadline")
    retriever = BlockingRetriever(0.25)
    registry = ToolRegistry()
    registry.register(
        ShortDeadlineSearch(session_factory=sqlite_session_factory, retriever=retriever)
    )
    try:
        with pytest.raises(ToolTimeoutError):
            await ToolExecutor(registry=registry).execute(
                ToolRequest(
                    tool_name="kb_search",
                    arguments={"knowledge_base_id": str(kb.id), "query": "test"},
                )
            )
        assert not retriever.finished.is_set()
    finally:
        # A canceled read-only thread finishes naturally; never tear down its DB early.
        await asyncio.to_thread(retriever.finished.wait, 2)


@pytest.mark.asyncio
async def test_blocking_search_keeps_lease_alive(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="heartbeat")
        agent = AgentRepository(session).create(name="search")
        repo = RunRepository(session)
        run = repo.create(
            agent_id=agent.id,
            input_payload={
                "tool": {
                    "name": "kb_search",
                    "arguments": {"knowledge_base_id": str(kb.id), "query": "test"},
                }
            },
        )
        repo.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={},
        )
    registry = ToolRegistry()
    registry.register(
        KnowledgeBaseSearchTool(
            session_factory=sqlite_session_factory, retriever=BlockingRetriever(1.25)
        )
    )
    with sqlite_session_factory() as session:
        result = await RunExecutionService(tool_registry=registry, lease_ttl_seconds=1).execute(
            run_id=run.id, repository=RunRepository(session)
        )
        assert result.status is RunStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_timed_out_search_cannot_complete_run_later(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="late")
        agent = AgentRepository(session).create(name="search")
        repo = RunRepository(session)
        run = repo.create(
            agent_id=agent.id,
            input_payload={
                "tool": {
                    "name": "kb_search",
                    "arguments": {"knowledge_base_id": str(kb.id), "query": "x"},
                }
            },
        )
        repo.apply_transition(
            run_id=run.id, status=RunStatus.QUEUED, event_type=RunEventType.RUN_QUEUED, payload={}
        )
    retriever = BlockingRetriever(0.25)
    registry = ToolRegistry()
    registry.register(
        ShortDeadlineSearch(session_factory=sqlite_session_factory, retriever=retriever)
    )
    try:
        with sqlite_session_factory() as session:
            result = await RunExecutionService(tool_registry=registry).execute(
                run_id=run.id, repository=RunRepository(session)
            )
            assert result.status is RunStatus.FAILED
            before = len(RunRepository(session).list_events(run.id))
        await asyncio.to_thread(retriever.finished.wait, 2)
        with sqlite_session_factory() as session:
            stored = RunRepository(session).get(run.id)
            assert stored is not None and stored.status is RunStatus.FAILED
            assert len(RunRepository(session).list_events(run.id)) == before
    finally:
        await asyncio.to_thread(retriever.finished.wait, 2)
