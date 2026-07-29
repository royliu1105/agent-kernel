"""Agent Kernel API entrypoint."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from kernel_core import Agent, Approval, ApprovalStatus, Document, KnowledgeBase, Run, RunEvent
from kernel_runtime import (
    InvalidRunTransitionError,
    RunExecutionError,
    RunExecutionService,
    RunNotFoundError,
    RunStateMachine,
)
from kernel_storage import (
    AgentRepository,
    ApprovalDecisionError,
    ApprovalRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    RunRepository,
    ToolCallRepository,
    create_engine_for_url,
    create_session_factory,
)
from sqlalchemy.orm import Session, sessionmaker

from agent_kernel_api.schemas import (
    AgentCreateRequest,
    AgentResponse,
    ApprovalApproveRequest,
    ApprovalRejectRequest,
    ApprovalResponse,
    DocumentCreateRequest,
    DocumentResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    RunCreateRequest,
    RunEventResponse,
    RunResponse,
    RunResumeRequest,
)


def create_app(
    session_factory: sessionmaker[Session] | None = None,
    execution_service: RunExecutionService | None = None,
) -> FastAPI:
    app = FastAPI(title="Agent Kernel API", version="0.1.0")
    factory = session_factory or create_session_factory(create_engine_for_url())
    runner = execution_service or RunExecutionService()

    def get_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "agent-kernel-api"}

    @app.post(
        "/v1/agents",
        response_model=AgentResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["agents"],
    )
    def create_agent(
        request: AgentCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> AgentResponse:
        agent = AgentRepository(session).create(
            name=request.name,
            description=request.description,
        )
        return _agent_response(agent)

    @app.get("/v1/agents/{agent_id}", response_model=AgentResponse, tags=["agents"])
    def get_agent(
        agent_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> AgentResponse:
        agent = AgentRepository(session).get(agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return _agent_response(agent)

    @app.post(
        "/v1/agents/{agent_id}/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["runs"],
    )
    def create_run(
        agent_id: UUID,
        request: RunCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        if AgentRepository(session).get(agent_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        run = RunRepository(session).create(agent_id=agent_id, input_payload=request.input)
        return _run_response(run)

    @app.get("/v1/runs/{run_id}", response_model=RunResponse, tags=["runs"])
    def get_run(
        run_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        run = RunRepository(session).get(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return _run_response(run)

    @app.get("/v1/runs/{run_id}/events", response_model=list[RunEventResponse], tags=["runs"])
    def list_run_events(
        run_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[RunEventResponse]:
        if RunRepository(session).get(run_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        events = RunRepository(session).list_events(run_id)
        return [_run_event_response(event) for event in events]

    @app.post("/v1/runs/{run_id}/queue", response_model=RunResponse, tags=["runs"])
    def queue_run(
        run_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        repository = RunRepository(session)
        run = repository.get(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        try:
            transition = RunStateMachine().queue(run)
        except InvalidRunTransitionError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        updated = repository.apply_transition(
            run_id=run.id,
            status=transition.to_status,
            event_type=transition.event_type,
            payload={
                "from_status": transition.from_status.value,
                "to_status": transition.to_status.value,
            },
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return _run_response(updated)

    @app.post("/v1/runs/{run_id}/cancel", response_model=RunResponse, tags=["runs"])
    def cancel_run(
        run_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        repository = RunRepository(session)
        run = repository.get(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        try:
            transition = RunStateMachine().cancel(run)
        except InvalidRunTransitionError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        updated = repository.apply_transition(
            run_id=run.id,
            status=transition.to_status,
            event_type=transition.event_type,
            payload={
                "from_status": transition.from_status.value,
                "to_status": transition.to_status.value,
            },
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return _run_response(updated)

    @app.post("/v1/runs/{run_id}/resume", response_model=RunResponse, tags=["runs"])
    async def resume_run(
        run_id: UUID,
        request: RunResumeRequest | None = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        try:
            run = await runner.resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
                approval_id=request.approval_id if request is not None else None,
            )
        except RunNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except (InvalidRunTransitionError, RunExecutionError) as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return _run_response(run)

    @app.get("/v1/approvals", response_model=list[ApprovalResponse], tags=["approvals"])
    def list_approvals(
        status_filter: Annotated[ApprovalStatus | None, Query(alias="status")] = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[ApprovalResponse]:
        approvals = ApprovalRepository(session).list(status=status_filter)
        return [_approval_response(approval) for approval in approvals]

    @app.get(
        "/v1/approvals/{approval_id}",
        response_model=ApprovalResponse,
        tags=["approvals"],
    )
    def get_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        approval = ApprovalRepository(session).get(approval_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return _approval_response(approval)

    @app.post(
        "/v1/approvals/{approval_id}/approve",
        response_model=ApprovalResponse,
        tags=["approvals"],
    )
    def approve_approval(
        approval_id: UUID,
        request: ApprovalApproveRequest | None = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        try:
            approval = ApprovalRepository(session).approve(
                approval_id=approval_id,
                decision_note=request.decision_note if request is not None else None,
            )
        except ApprovalDecisionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return _approval_response(approval)

    @app.post(
        "/v1/approvals/{approval_id}/reject",
        response_model=ApprovalResponse,
        tags=["approvals"],
    )
    def reject_approval(
        approval_id: UUID,
        request: ApprovalRejectRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        try:
            approval = ApprovalRepository(session).reject(
                approval_id=approval_id,
                decision_note=request.reason,
            )
        except ApprovalDecisionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return _approval_response(approval)

    @app.post(
        "/v1/knowledge-bases",
        response_model=KnowledgeBaseResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["knowledge-bases"],
    )
    def create_knowledge_base(
        request: KnowledgeBaseCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> KnowledgeBaseResponse:
        knowledge_base = KnowledgeBaseRepository(session).create(
            name=request.name,
            description=request.description,
            metadata=request.metadata,
        )
        return _knowledge_base_response(knowledge_base)

    @app.get(
        "/v1/knowledge-bases",
        response_model=list[KnowledgeBaseResponse],
        tags=["knowledge-bases"],
    )
    def list_knowledge_bases(
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[KnowledgeBaseResponse]:
        knowledge_bases = KnowledgeBaseRepository(session).list()
        return [_knowledge_base_response(knowledge_base) for knowledge_base in knowledge_bases]

    @app.get(
        "/v1/knowledge-bases/{knowledge_base_id}",
        response_model=KnowledgeBaseResponse,
        tags=["knowledge-bases"],
    )
    def get_knowledge_base(
        knowledge_base_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> KnowledgeBaseResponse:
        knowledge_base = KnowledgeBaseRepository(session).get(knowledge_base_id)
        if knowledge_base is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return _knowledge_base_response(knowledge_base)

    @app.post(
        "/v1/knowledge-bases/{knowledge_base_id}/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    def create_document(
        knowledge_base_id: UUID,
        request: DocumentCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base_id,
            title=request.title,
            source_uri=request.source_uri,
            mime_type=request.mime_type,
            checksum=request.checksum,
            size_bytes=request.size_bytes,
            metadata=request.metadata,
        )
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return _document_response(document)

    @app.get(
        "/v1/knowledge-bases/{knowledge_base_id}/documents",
        response_model=list[DocumentResponse],
        tags=["documents"],
    )
    def list_documents(
        knowledge_base_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentResponse]:
        documents = DocumentRepository(session).list_for_knowledge_base(knowledge_base_id)
        if documents is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return [_document_response(document) for document in documents]

    @app.get(
        "/v1/documents/{document_id}",
        response_model=DocumentResponse,
        tags=["documents"],
    )
    def get_document(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        document = DocumentRepository(session).get(document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return _document_response(document)

    return app


app = create_app()


def main() -> None:
    uvicorn.run("agent_kernel_api.main:app", host="0.0.0.0", port=8000, reload=False)


def _agent_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        prompt_id=agent.prompt_id,
        default_model_policy_id=agent.default_model_policy_id,
        memory_policy=agent.memory_policy,
        tool_policy=agent.tool_policy,
        metadata=agent.metadata,
        created_at=agent.created_at,
    )


def _run_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        agent_id=run.agent_id,
        status=run.status,
        input=run.input,
        output=run.output,
        trace_id=run.trace_id,
        error_type=run.error_type,
        error_message=run.error_message,
        input_tokens_total=run.input_tokens_total,
        output_tokens_total=run.output_tokens_total,
        estimated_cost_total=run.estimated_cost_total,
        started_at=run.started_at,
        ended_at=run.ended_at,
        created_at=run.created_at,
    )


def _run_event_response(event: RunEvent) -> RunEventResponse:
    return RunEventResponse(
        id=event.id,
        run_id=event.run_id,
        sequence=event.sequence,
        type=event.type,
        payload=event.payload,
        trace_id=event.trace_id,
        created_at=event.created_at,
    )


def _approval_response(approval: Approval) -> ApprovalResponse:
    return ApprovalResponse(
        id=approval.id,
        run_id=approval.run_id,
        tool_call_id=approval.tool_call_id,
        status=approval.status,
        reason=approval.reason,
        requested_by=approval.requested_by,
        reviewed_by=approval.reviewed_by,
        decision_note=approval.decision_note,
        trace_id=approval.trace_id,
        requested_at=approval.requested_at,
        resolved_at=approval.resolved_at,
    )


def _knowledge_base_response(knowledge_base: KnowledgeBase) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=knowledge_base.id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        status=knowledge_base.status,
        metadata=knowledge_base.metadata,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        title=document.title,
        source_uri=document.source_uri,
        mime_type=document.mime_type,
        checksum=document.checksum,
        size_bytes=document.size_bytes,
        status=document.status,
        error_message=document.error_message,
        metadata=document.metadata,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
