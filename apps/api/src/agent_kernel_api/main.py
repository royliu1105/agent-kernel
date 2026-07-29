"""Agent Kernel API entrypoint."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from kernel_core import (
    Agent,
    Approval,
    ApprovalStatus,
    ChunkEmbedding,
    Document,
    DocumentChunk,
    DocumentStatus,
    IngestionJob,
    KnowledgeBase,
    Run,
    RunEvent,
)
from kernel_rag import (
    DocumentChunkingService,
    DocumentIndexingService,
    DocumentIngestionService,
    DocumentNotChunkableError,
    DocumentNotFoundError,
    DocumentNotIndexableError,
    DocumentNotReadyError,
    LocalObjectStore,
    ObjectTooLargeError,
)
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
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
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
    ChunkEmbeddingResponse,
    DocumentChunkResponse,
    DocumentCreateRequest,
    DocumentIndexResponse,
    DocumentResponse,
    IngestionJobResponse,
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
    object_store: LocalObjectStore | None = None,
    ingestion_service: DocumentIngestionService | None = None,
    chunking_service: DocumentChunkingService | None = None,
    indexing_service: DocumentIndexingService | None = None,
) -> FastAPI:
    app = FastAPI(title="Agent Kernel API", version="0.1.0")
    factory = session_factory or create_session_factory(create_engine_for_url())
    runner = execution_service or RunExecutionService()
    store = object_store or LocalObjectStore()
    ingester = ingestion_service or DocumentIngestionService(object_store=store)
    chunker = chunking_service or DocumentChunkingService(object_store=store)
    indexer = indexing_service or DocumentIndexingService()

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

    @app.post(
        "/v1/knowledge-bases/{knowledge_base_id}/documents/upload",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    async def upload_document(
        knowledge_base_id: UUID,
        file: Annotated[UploadFile, File(description="Document file to upload.")],
        title: Annotated[str | None, Form(max_length=500)] = None,
        metadata: Annotated[str, Form()] = "{}",
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        if KnowledgeBaseRepository(session).get(knowledge_base_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        metadata_payload = _parse_metadata_json(metadata)
        filename = file.filename or "document"
        content = await file.read(store.max_object_bytes + 1)
        try:
            stored = store.write_document(
                knowledge_base_id=knowledge_base_id,
                filename=filename,
                content=content,
                content_type=file.content_type,
            )
        except ObjectTooLargeError as error:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=str(error),
            ) from error

        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base_id,
            title=title or filename,
            source_uri=stored.uri,
            mime_type=stored.content_type,
            checksum=stored.checksum,
            size_bytes=stored.size_bytes,
            status=DocumentStatus.UPLOADED,
            metadata={
                **metadata_payload,
                "object_key": stored.key,
                "original_filename": filename,
            },
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

    @app.post(
        "/v1/documents/{document_id}/chunk",
        response_model=list[DocumentChunkResponse],
        status_code=status.HTTP_201_CREATED,
        tags=["chunks"],
    )
    def chunk_document(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentChunkResponse]:
        try:
            chunks = chunker.chunk_document(
                document_id=document_id,
                document_repository=DocumentRepository(session),
                ingestion_job_repository=IngestionJobRepository(session),
                chunk_repository=DocumentChunkRepository(session),
            )
        except DocumentNotChunkableError as error:
            if "was not found" in str(error):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(error),
                ) from error
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return [_document_chunk_response(chunk) for chunk in chunks]

    @app.get(
        "/v1/documents/{document_id}/chunks",
        response_model=list[DocumentChunkResponse],
        tags=["chunks"],
    )
    def list_document_chunks(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentChunkResponse]:
        chunks = DocumentChunkRepository(session).list_for_document(document_id)
        if chunks is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_document_chunk_response(chunk) for chunk in chunks]

    @app.get(
        "/v1/document-chunks/{chunk_id}",
        response_model=DocumentChunkResponse,
        tags=["chunks"],
    )
    def get_document_chunk(
        chunk_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentChunkResponse:
        chunk = DocumentChunkRepository(session).get(chunk_id)
        if chunk is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document chunk not found",
            )
        return _document_chunk_response(chunk)

    @app.post(
        "/v1/documents/{document_id}/index",
        response_model=DocumentIndexResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["embeddings"],
    )
    def index_document(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentIndexResponse:
        try:
            result = indexer.index_document(
                document_id=document_id,
                document_repository=DocumentRepository(session),
                chunk_repository=DocumentChunkRepository(session),
                embedding_repository=ChunkEmbeddingRepository(session),
            )
        except DocumentNotIndexableError as error:
            if "was not found" in str(error):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(error),
                ) from error
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return DocumentIndexResponse(
            document_id=result.document_id,
            model=result.model,
            dimensions=result.dimensions,
            embedding_count=result.embedding_count,
        )

    @app.get(
        "/v1/documents/{document_id}/embeddings",
        response_model=list[ChunkEmbeddingResponse],
        tags=["embeddings"],
    )
    def list_document_embeddings(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[ChunkEmbeddingResponse]:
        embeddings = ChunkEmbeddingRepository(session).list_for_document(document_id=document_id)
        if embeddings is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_chunk_embedding_response(embedding) for embedding in embeddings]

    @app.post(
        "/v1/documents/{document_id}/ingest",
        response_model=IngestionJobResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["ingestion"],
    )
    def ingest_document(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> IngestionJobResponse:
        try:
            job = ingester.ingest(
                document_id=document_id,
                document_repository=DocumentRepository(session),
                ingestion_job_repository=IngestionJobRepository(session),
            )
        except DocumentNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except DocumentNotReadyError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return _ingestion_job_response(job)

    @app.get(
        "/v1/documents/{document_id}/ingestion-jobs",
        response_model=list[IngestionJobResponse],
        tags=["ingestion"],
    )
    def list_document_ingestion_jobs(
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[IngestionJobResponse]:
        jobs = IngestionJobRepository(session).list_for_document(document_id)
        if jobs is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_ingestion_job_response(job) for job in jobs]

    @app.get(
        "/v1/ingestion-jobs/{job_id}",
        response_model=IngestionJobResponse,
        tags=["ingestion"],
    )
    def get_ingestion_job(
        job_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> IngestionJobResponse:
        job = IngestionJobRepository(session).get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion job not found",
            )
        return _ingestion_job_response(job)

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


def _parse_metadata_json(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata JSON: {error.msg}",
        ) from error
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Metadata must be a JSON object",
        )
    return parsed


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


def _document_chunk_response(chunk: DocumentChunk) -> DocumentChunkResponse:
    return DocumentChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        index=chunk.index,
        content=chunk.content,
        start_char=chunk.start_char,
        end_char=chunk.end_char,
        token_count_estimate=chunk.token_count_estimate,
        checksum=chunk.checksum,
        metadata=chunk.metadata,
        created_at=chunk.created_at,
    )


def _chunk_embedding_response(embedding: ChunkEmbedding) -> ChunkEmbeddingResponse:
    return ChunkEmbeddingResponse(
        id=embedding.id,
        document_id=embedding.document_id,
        chunk_id=embedding.chunk_id,
        model=embedding.model,
        dimensions=embedding.dimensions,
        vector=embedding.vector,
        checksum=embedding.checksum,
        metadata=embedding.metadata,
        created_at=embedding.created_at,
    )


def _ingestion_job_response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        parser_name=job.parser_name,
        parsed_text_uri=job.parsed_text_uri,
        parsed_text_checksum=job.parsed_text_checksum,
        parsed_text_size_bytes=job.parsed_text_size_bytes,
        content_char_count=job.content_char_count,
        error_type=job.error_type,
        error_message=job.error_message,
        metadata=job.metadata,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
