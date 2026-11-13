"""Agent Kernel API entrypoint."""

from __future__ import annotations

import json
import logging
import os
import secrets
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response
from kernel_core import (
    Agent,
    Approval,
    ApprovalStatus,
    ChunkEmbedding,
    Document,
    DocumentChunk,
    DocumentStatus,
    EvalRun,
    EvalRunStatus,
    IngestionJob,
    KnowledgeBase,
    MemoryItem,
    MemoryType,
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
)
from kernel_identity import Permission
from kernel_observability import (
    AggregatingMetricsRecorder,
    ExposableMetricsRecorder,
    HttpMetricsMiddleware,
    configure_opentelemetry,
    configure_safe_logging,
    uvicorn_log_config,
)
from kernel_rag import (
    DocumentChunkingService,
    DocumentIndexingService,
    DocumentIngestionService,
    DocumentNotChunkableError,
    DocumentNotFoundError,
    DocumentNotIndexableError,
    DocumentNotReadyError,
    ObjectStore,
    ObjectTooLargeError,
    Retriever,
    create_embedding_provider,
    create_object_store,
    create_rag_tool_registry,
)
from kernel_rag import (
    KnowledgeBaseNotFoundError as RetrievalKnowledgeBaseNotFoundError,
)
from kernel_rag import (
    RetrievalResponse as RagRetrievalResponse,
)
from kernel_runtime import (
    InvalidRunTransitionError,
    RunExecutionError,
    RunExecutionService,
    RunNotFoundError,
    RunStateMachine,
    create_default_model_router,
)
from kernel_runtime.queue import QueueUnavailableError, RunQueue
from kernel_runtime.redis_support import (
    RedisSettings,
    RedisWorkspaceRateLimiter,
    create_redis_client,
    create_run_queue,
)
from kernel_storage import (
    AgentRepository,
    ApprovalDecisionError,
    ApprovalRepository,
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    EvalRunRepository,
    ExecutionOwnershipError,
    IngestionJobRepository,
    KnowledgeBaseRepository,
    MemoryRepository,
    RunConflictError,
    RunRepository,
    ToolCallRepository,
    create_engine_for_url,
    create_session_factory,
)
from kernel_storage.models import ApprovalRecord, EvalRunRecord, RunEventRecord, RunRecord
from kernel_tools.external.config import external_tools_config_from_env
from kernel_tools.external.loader import load_external_tools
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from agent_kernel_api.auth import (
    ApiKeyAuthMiddleware,
    api_key_auth_enabled_from_env,
    current_principal_id,
    current_workspace_id,
    require_permission,
)
from agent_kernel_api.readiness import ReadinessChecker, create_readiness_checker
from agent_kernel_api.schemas import (
    AgentCreateRequest,
    AgentResponse,
    ApprovalApproveRequest,
    ApprovalRejectRequest,
    ApprovalResponse,
    ChunkEmbeddingResponse,
    CitationResponse,
    DocumentChunkResponse,
    DocumentCreateRequest,
    DocumentIndexResponse,
    DocumentResponse,
    EvalRunCreateRequest,
    EvalRunResponse,
    IngestionJobResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryResponse,
    RetrievalRequest,
    RetrievalResponseModel,
    RetrievalResultResponse,
    RunCreateRequest,
    RunEventResponse,
    RunResponse,
    RunResumeRequest,
)


def create_app(
    session_factory: sessionmaker[Session] | None = None,
    execution_service: RunExecutionService | None = None,
    object_store: ObjectStore | None = None,
    ingestion_service: DocumentIngestionService | None = None,
    chunking_service: DocumentChunkingService | None = None,
    indexing_service: DocumentIndexingService | None = None,
    retriever: Retriever | None = None,
    metrics_recorder: ExposableMetricsRecorder | None = None,
    api_key_auth_enabled: bool | None = None,
    run_queue: RunQueue | None = None,
    rate_limiter: RedisWorkspaceRateLimiter | None = None,
    readiness_checker: ReadinessChecker | None = None,
) -> FastAPI:
    configure_safe_logging()
    configure_opentelemetry()
    factory = session_factory or create_session_factory(create_engine_for_url())
    auth_enabled = api_key_auth_enabled
    if auth_enabled is None:
        auth_enabled = api_key_auth_enabled_from_env()
    redis_settings = RedisSettings.from_env()
    rate_limit = int(os.getenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "0"))
    principal_rate_limit = int(os.getenv("AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS", "0"))
    api_key_rate_limit = int(os.getenv("AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS", "0"))
    rate_window = int(os.getenv("AGENT_KERNEL_RATE_LIMIT_WINDOW_SECONDS", "60"))
    rates = (rate_limit, principal_rate_limit, api_key_rate_limit)
    if any(not 0 <= rate <= 1_000_000 for rate in rates) or not 1 <= rate_window <= 86400:
        raise ValueError("Invalid rate-limit bounds.")
    rate_limiting_enabled = any(rates)
    if rate_limiting_enabled and not auth_enabled:
        raise ValueError("Rate limiting requires API key authentication.")
    needs_redis = (run_queue is None and redis_settings.queue_backend == "redis") or (
        rate_limiting_enabled and rate_limiter is None
    )
    redis_client = create_redis_client(redis_settings) if needs_redis else None
    queue = run_queue or create_run_queue(redis_settings, client=redis_client)
    limiter = rate_limiter
    if rate_limiting_enabled and limiter is None:
        assert redis_client is not None
        limiter = RedisWorkspaceRateLimiter(
            client=redis_client,
            prefix=redis_settings.rate_limit_prefix,
        )
    readiness = readiness_checker or create_readiness_checker(
        factory,
        redis_probe=redis_client.ping if redis_client is not None else None,
    )
    process_metrics = metrics_recorder or AggregatingMetricsRecorder()
    retrieval_service = retriever or Retriever(
        embedding_provider=create_embedding_provider(), metrics_recorder=process_metrics
    )
    registry = create_rag_tool_registry(
        session_factory=factory,
        metrics_recorder=process_metrics,
        retriever=retrieval_service,
    )
    external_config = external_tools_config_from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            async with load_external_tools(registry, external_config):
                yield
        finally:
            readiness.close()
            if redis_client is not None:
                redis_client.close()

    app = FastAPI(title="Agent Kernel API", version="1.0.0", lifespan=lifespan)
    if auth_enabled:
        app.add_middleware(
            ApiKeyAuthMiddleware,
            session_factory=factory,
            rate_limiter=limiter,
            rate_limit=rate_limit,
            principal_rate_limit=principal_rate_limit,
            api_key_rate_limit=api_key_rate_limit,
            rate_window_seconds=rate_window,
        )
    app.add_middleware(HttpMetricsMiddleware, metrics=process_metrics)

    runner = execution_service or RunExecutionService(
        router=create_default_model_router(),
        metrics_recorder=process_metrics,
        tool_registry=registry,
    )
    store = object_store or create_object_store()
    ingester = ingestion_service or DocumentIngestionService(object_store=store)
    chunker = chunking_service or DocumentChunkingService(object_store=store)
    indexer = indexing_service or DocumentIndexingService(
        embedding_provider=retrieval_service.embedding_provider
    )

    @app.exception_handler(ExecutionOwnershipError)
    @app.exception_handler(RunConflictError)
    async def execution_conflict(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": "Run changed; refresh its state."})

    def get_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "agent-kernel-api"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> JSONResponse:
        result = await readiness.check()
        return JSONResponse(status_code=result.status_code, content=result.to_dict())

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> Response:
        token = os.getenv("AGENT_KERNEL_MONITORING_TOKEN", "")
        if auth_enabled or token:
            supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
            if not token or not secrets.compare_digest(token.encode(), supplied.encode()):
                raise HTTPException(status_code=401, detail="Monitoring authentication required.")
        try:
            snapshot = _operational_metrics(factory)
        except Exception:
            logging.getLogger(__name__).exception("Operational metrics snapshot failed")
            raise HTTPException(
                status_code=503, detail="Operational metrics unavailable."
            ) from None
        return Response(
            content=process_metrics.prometheus_text() + snapshot,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get(
        "/v1/usage",
        dependencies=[Depends(require_permission(Permission.RUN_READ))],
        tags=["runs"],
    )
    def usage_summary(
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> dict[str, object]:
        return RunRepository(session).usage_summary(
            workspace_id=current_workspace_id(http_request),
        )

    @app.get(
        "/v1/usage/breakdown",
        dependencies=[Depends(require_permission(Permission.RUN_READ))],
        tags=["runs"],
    )
    def usage_breakdown(
        http_request: Request,
        group_by: Literal["workspace", "run", "principal", "model"] = "model",
        run_id: UUID | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        session: Session = Depends(get_session),  # noqa: B008
    ) -> dict[str, object]:
        return {
            "group_by": group_by,
            "items": RunRepository(session).usage_breakdown(
                group_by=group_by,
                workspace_id=current_workspace_id(http_request),
                run_id=run_id,
                limit=limit,
            ),
            "estimated": True,
        }

    @app.post(
        "/v1/agents",
        response_model=AgentResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.AGENT_WRITE))],
        tags=["agents"],
    )
    def create_agent(
        request: AgentCreateRequest,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> AgentResponse:
        agent = AgentRepository(session).create(
            name=request.name,
            description=request.description,
            workspace_id=current_workspace_id(http_request),
        )
        return _agent_response(agent)

    @app.get(
        "/v1/agents/{agent_id}",
        response_model=AgentResponse,
        dependencies=[Depends(require_permission(Permission.AGENT_READ))],
        tags=["agents"],
    )
    def get_agent(
        agent_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> AgentResponse:
        agent = AgentRepository(session).get(
            agent_id,
            workspace_id=current_workspace_id(http_request),
        )
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return _agent_response(agent)

    @app.post(
        "/v1/agents/{agent_id}/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.RUN_WRITE))],
        tags=["runs"],
    )
    def create_run(
        agent_id: UUID,
        request: RunCreateRequest,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        workspace_id = current_workspace_id(http_request)
        agent = AgentRepository(session).get(agent_id, workspace_id=workspace_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        run = RunRepository(session).create(
            agent_id=agent_id,
            workspace_id=workspace_id,
            principal_id=current_principal_id(http_request),
            input_payload=request.input,
        )
        return _run_response(run)

    @app.get(
        "/v1/runs/{run_id}",
        response_model=RunResponse,
        dependencies=[Depends(require_permission(Permission.RUN_READ))],
        tags=["runs"],
    )
    def get_run(
        run_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        run = RunRepository(session).get(run_id, workspace_id=current_workspace_id(http_request))
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return _run_response(run)

    @app.get(
        "/v1/runs/{run_id}/events",
        response_model=list[RunEventResponse],
        dependencies=[Depends(require_permission(Permission.RUN_READ))],
        tags=["runs"],
    )
    def list_run_events(
        run_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[RunEventResponse]:
        run = RunRepository(session).get(
            run_id,
            workspace_id=current_workspace_id(http_request),
        )
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        events = RunRepository(session).list_events(run_id)
        return [_run_event_response(event) for event in events]

    @app.post(
        "/v1/runs/{run_id}/queue",
        response_model=RunResponse,
        dependencies=[Depends(require_permission(Permission.RUN_WRITE))],
        tags=["runs"],
    )
    def queue_run(
        run_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        repository = RunRepository(session)
        run = repository.get(run_id, workspace_id=current_workspace_id(http_request))
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
        if queue is not None:
            try:
                queue.enqueue(updated.id)
            except QueueUnavailableError:
                process_metrics.increment("run_queue_errors_total", labels={"operation": "enqueue"})
        return _run_response(updated)

    @app.post(
        "/v1/runs/{run_id}/cancel",
        response_model=RunResponse,
        dependencies=[Depends(require_permission(Permission.RUN_WRITE))],
        tags=["runs"],
    )
    def cancel_run(
        run_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        repository = RunRepository(session)
        run = repository.get(run_id, workspace_id=current_workspace_id(http_request))
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

    @app.post(
        "/v1/runs/{run_id}/resume",
        response_model=RunResponse,
        dependencies=[Depends(require_permission(Permission.RUN_WRITE))],
        tags=["runs"],
    )
    async def resume_run(
        run_id: UUID,
        http_request: Request,
        request: RunResumeRequest | None = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RunResponse:
        try:
            workspace_id = current_workspace_id(http_request)
            if RunRepository(session).get(run_id, workspace_id=workspace_id) is None:
                raise RunNotFoundError(f"Run {run_id} was not found.")
            if request is not None and request.approval_id is not None:
                approval = ApprovalRepository(session).get(
                    request.approval_id,
                    workspace_id=workspace_id,
                )
                if approval is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Approval not found",
                    )
                if approval.run_id != run_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Approval {approval.id} does not belong to run {run_id}.",
                    )
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

    @app.get(
        "/v1/approvals",
        response_model=list[ApprovalResponse],
        dependencies=[Depends(require_permission(Permission.APPROVAL_REVIEW))],
        tags=["approvals"],
    )
    def list_approvals(
        http_request: Request,
        status_filter: Annotated[ApprovalStatus | None, Query(alias="status")] = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[ApprovalResponse]:
        approvals = ApprovalRepository(session).list(
            status=status_filter,
            workspace_id=current_workspace_id(http_request),
        )
        return [_approval_response(approval) for approval in approvals]

    @app.get(
        "/v1/approvals/{approval_id}",
        response_model=ApprovalResponse,
        dependencies=[Depends(require_permission(Permission.APPROVAL_REVIEW))],
        tags=["approvals"],
    )
    def get_approval(
        approval_id: UUID,
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        approval = ApprovalRepository(session).get(
            approval_id,
            workspace_id=current_workspace_id(http_request),
        )
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return _approval_response(approval)

    @app.post(
        "/v1/approvals/{approval_id}/approve",
        response_model=ApprovalResponse,
        dependencies=[Depends(require_permission(Permission.APPROVAL_REVIEW))],
        tags=["approvals"],
    )
    def approve_approval(
        approval_id: UUID,
        http_request: Request,
        request: ApprovalApproveRequest | None = None,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        try:
            approval = ApprovalRepository(session).approve(
                approval_id=approval_id,
                reviewed_by=current_principal_id(http_request),
                decision_note=request.decision_note if request is not None else None,
                workspace_id=current_workspace_id(http_request),
            )
        except ApprovalDecisionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return _approval_response(approval)

    @app.post(
        "/v1/memory",
        response_model=MemoryResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.MEMORY_WRITE))],
        tags=["memory"],
    )
    def create_memory(
        http_request: Request,
        request: MemoryCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> MemoryResponse:
        try:
            memory = MemoryRepository(
                session, workspace_id=current_workspace_id(http_request)
            ).create(
                type=request.type,
                scope=request.scope,
                content=request.content,
                source_run_id=request.source_run_id,
                confidence=request.confidence,
                metadata=request.metadata,
            )
        except ValueError as error:
            raise HTTPException(status_code=404, detail="Source run not found") from error
        return _memory_response(memory)

    @app.get(
        "/v1/memory",
        response_model=list[MemoryResponse],
        dependencies=[Depends(require_permission(Permission.MEMORY_READ))],
        tags=["memory"],
    )
    def list_memory(
        http_request: Request,
        scope: str | None = None,
        type_filter: Annotated[MemoryType | None, Query(alias="type")] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[MemoryResponse]:
        memories = MemoryRepository(session, workspace_id=current_workspace_id(http_request)).list(
            scope=scope,
            type=type_filter,
            limit=limit,
        )
        return [_memory_response(memory) for memory in memories]

    @app.get(
        "/v1/memory/{memory_id}",
        response_model=MemoryResponse,
        dependencies=[Depends(require_permission(Permission.MEMORY_READ))],
        tags=["memory"],
    )
    def get_memory(
        http_request: Request,
        memory_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> MemoryResponse:
        memory = MemoryRepository(session, workspace_id=current_workspace_id(http_request)).get(
            memory_id
        )
        if memory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return _memory_response(memory)

    @app.delete(
        "/v1/memory/{memory_id}",
        response_model=MemoryDeleteResponse,
        dependencies=[Depends(require_permission(Permission.MEMORY_WRITE))],
        tags=["memory"],
    )
    def delete_memory(
        http_request: Request,
        memory_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> MemoryDeleteResponse:
        deleted = MemoryRepository(session, workspace_id=current_workspace_id(http_request)).delete(
            memory_id
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return MemoryDeleteResponse(id=memory_id, deleted=True)

    @app.post(
        "/v1/approvals/{approval_id}/reject",
        response_model=ApprovalResponse,
        dependencies=[Depends(require_permission(Permission.APPROVAL_REVIEW))],
        tags=["approvals"],
    )
    def reject_approval(
        approval_id: UUID,
        http_request: Request,
        request: ApprovalRejectRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> ApprovalResponse:
        try:
            approval = ApprovalRepository(session).reject(
                approval_id=approval_id,
                decision_note=request.reason,
                reviewed_by=current_principal_id(http_request),
                workspace_id=current_workspace_id(http_request),
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["knowledge-bases"],
    )
    def create_knowledge_base(
        http_request: Request,
        request: KnowledgeBaseCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> KnowledgeBaseResponse:
        knowledge_base = KnowledgeBaseRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).create(
            name=request.name,
            description=request.description,
            metadata=request.metadata,
        )
        return _knowledge_base_response(knowledge_base)

    @app.get(
        "/v1/knowledge-bases",
        response_model=list[KnowledgeBaseResponse],
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["knowledge-bases"],
    )
    def list_knowledge_bases(
        http_request: Request,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[KnowledgeBaseResponse]:
        knowledge_bases = KnowledgeBaseRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list()
        return [_knowledge_base_response(knowledge_base) for knowledge_base in knowledge_bases]

    @app.get(
        "/v1/knowledge-bases/{knowledge_base_id}",
        response_model=KnowledgeBaseResponse,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["knowledge-bases"],
    )
    def get_knowledge_base(
        http_request: Request,
        knowledge_base_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> KnowledgeBaseResponse:
        knowledge_base = KnowledgeBaseRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).get(knowledge_base_id)
        if knowledge_base is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return _knowledge_base_response(knowledge_base)

    @app.post(
        "/v1/knowledge-bases/{knowledge_base_id}/retrieve",
        response_model=RetrievalResponseModel,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["retrieval"],
    )
    def retrieve_from_knowledge_base(
        http_request: Request,
        knowledge_base_id: UUID,
        request: RetrievalRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> RetrievalResponseModel:
        try:
            response = retrieval_service.retrieve(
                knowledge_base_id=knowledge_base_id,
                query=request.query,
                top_k=request.top_k,
                knowledge_base_repository=KnowledgeBaseRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                document_repository=DocumentRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                chunk_repository=DocumentChunkRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                embedding_repository=ChunkEmbeddingRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
            )
        except RetrievalKnowledgeBaseNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        return _retrieval_response(response)

    @app.post(
        "/v1/evals/runs",
        response_model=EvalRunResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.EVAL_WRITE))],
        tags=["evals"],
    )
    def create_eval_run(
        http_request: Request,
        request: EvalRunCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> EvalRunResponse:
        try:
            eval_run = EvalRunRepository(
                session, workspace_id=current_workspace_id(http_request)
            ).create_from_report(
                name=request.name,
                suite_type=request.suite_type,
                report=request.report,
                metadata=request.metadata,
                error_type=request.error_type,
                error_message=request.error_message,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        return _eval_run_response(eval_run)

    @app.get(
        "/v1/evals/runs",
        response_model=list[EvalRunResponse],
        dependencies=[Depends(require_permission(Permission.EVAL_READ))],
        tags=["evals"],
    )
    def list_eval_runs(
        http_request: Request,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[EvalRunResponse]:
        eval_runs = EvalRunRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list(limit=limit)
        return [_eval_run_response(eval_run) for eval_run in eval_runs]

    @app.get(
        "/v1/evals/runs/{eval_run_id}",
        response_model=EvalRunResponse,
        dependencies=[Depends(require_permission(Permission.EVAL_READ))],
        tags=["evals"],
    )
    def get_eval_run(
        http_request: Request,
        eval_run_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> EvalRunResponse:
        eval_run = EvalRunRepository(session, workspace_id=current_workspace_id(http_request)).get(
            eval_run_id
        )
        if eval_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
        return _eval_run_response(eval_run)

    @app.post(
        "/v1/knowledge-bases/{knowledge_base_id}/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["documents"],
    )
    def create_document(
        http_request: Request,
        knowledge_base_id: UUID,
        request: DocumentCreateRequest,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        try:
            document = DocumentRepository(
                session, workspace_id=current_workspace_id(http_request)
            ).create(
                knowledge_base_id=knowledge_base_id,
                title=request.title,
                source_uri=request.source_uri,
                mime_type=request.mime_type,
                checksum=request.checksum,
                size_bytes=request.size_bytes,
                metadata=request.metadata,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            ) from error
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["documents"],
    )
    async def upload_document(
        http_request: Request,
        knowledge_base_id: UUID,
        file: Annotated[UploadFile, File(description="Document file to upload.")],
        title: Annotated[str | None, Form(max_length=500)] = None,
        metadata: Annotated[str, Form()] = "{}",
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        if (
            KnowledgeBaseRepository(session, workspace_id=current_workspace_id(http_request)).get(
                knowledge_base_id
            )
            is None
        ):
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

        document = DocumentRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).create(
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["documents"],
    )
    def list_documents(
        http_request: Request,
        knowledge_base_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentResponse]:
        documents = DocumentRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list_for_knowledge_base(knowledge_base_id)
        if documents is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return [_document_response(document) for document in documents]

    @app.get(
        "/v1/documents/{document_id}",
        response_model=DocumentResponse,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["documents"],
    )
    def get_document(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentResponse:
        document = DocumentRepository(session, workspace_id=current_workspace_id(http_request)).get(
            document_id
        )
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return _document_response(document)

    @app.post(
        "/v1/documents/{document_id}/chunk",
        response_model=list[DocumentChunkResponse],
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["chunks"],
    )
    def chunk_document(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentChunkResponse]:
        try:
            chunks = chunker.chunk_document(
                document_id=document_id,
                document_repository=DocumentRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                ingestion_job_repository=IngestionJobRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                chunk_repository=DocumentChunkRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["chunks"],
    )
    def list_document_chunks(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[DocumentChunkResponse]:
        chunks = DocumentChunkRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list_for_document(document_id)
        if chunks is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_document_chunk_response(chunk) for chunk in chunks]

    @app.get(
        "/v1/document-chunks/{chunk_id}",
        response_model=DocumentChunkResponse,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["chunks"],
    )
    def get_document_chunk(
        http_request: Request,
        chunk_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentChunkResponse:
        chunk = DocumentChunkRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).get(chunk_id)
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["embeddings"],
    )
    def index_document(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> DocumentIndexResponse:
        try:
            result = indexer.index_document(
                document_id=document_id,
                document_repository=DocumentRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                chunk_repository=DocumentChunkRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                embedding_repository=ChunkEmbeddingRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
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
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["embeddings"],
    )
    def list_document_embeddings(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[ChunkEmbeddingResponse]:
        embeddings = ChunkEmbeddingRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list_for_document(document_id=document_id)
        if embeddings is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_chunk_embedding_response(embedding) for embedding in embeddings]

    @app.post(
        "/v1/documents/{document_id}/ingest",
        response_model=IngestionJobResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_WRITE))],
        tags=["ingestion"],
    )
    def ingest_document(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> IngestionJobResponse:
        try:
            job = ingester.ingest(
                document_id=document_id,
                document_repository=DocumentRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
                ingestion_job_repository=IngestionJobRepository(
                    session, workspace_id=current_workspace_id(http_request)
                ),
            )
        except DocumentNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except DocumentNotReadyError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return _ingestion_job_response(job)

    @app.get(
        "/v1/documents/{document_id}/ingestion-jobs",
        response_model=list[IngestionJobResponse],
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["ingestion"],
    )
    def list_document_ingestion_jobs(
        http_request: Request,
        document_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> list[IngestionJobResponse]:
        jobs = IngestionJobRepository(
            session, workspace_id=current_workspace_id(http_request)
        ).list_for_document(document_id)
        if jobs is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return [_ingestion_job_response(job) for job in jobs]

    @app.get(
        "/v1/ingestion-jobs/{job_id}",
        response_model=IngestionJobResponse,
        dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
        tags=["ingestion"],
    )
    def get_ingestion_job(
        http_request: Request,
        job_id: UUID,
        session: Session = Depends(get_session),  # noqa: B008
    ) -> IngestionJobResponse:
        job = IngestionJobRepository(session, workspace_id=current_workspace_id(http_request)).get(
            job_id
        )
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion job not found",
            )
        return _ingestion_job_response(job)

    return app


def _operational_metrics(factory: sessionmaker[Session]) -> str:
    """Read durable, deployment-wide state for the monitoring endpoint.

    These are gauges, not counters: retention/deletion can lower persisted totals.
    No payload columns, tenant selectors, identifiers or unbounded labels are read.
    """
    lines: list[str] = []
    now = datetime.now(UTC)

    def gauge(name: str, help_text: str, value: float) -> None:
        lines.extend((f"# HELP {name} {help_text}", f"# TYPE {name} gauge", f"{name} {value}"))

    def age(value: datetime | None) -> float:
        if value is None:
            return 0
        return max(0, (now - value.replace(tzinfo=value.tzinfo or UTC)).total_seconds())

    with factory() as session:
        for name, column, allowed in (
            ("agent_kernel_runs", RunRecord.status, tuple(status.value for status in RunStatus)),
            (
                "agent_kernel_evals",
                EvalRunRecord.status,
                tuple(status.value for status in EvalRunStatus),
            ),
            (
                "agent_kernel_approvals",
                ApprovalRecord.status,
                tuple(status.value for status in ApprovalStatus),
            ),
            (
                "agent_kernel_run_events",
                RunEventRecord.type,
                tuple(event.value for event in RunEventType if event.value.startswith("run_")),
            ),
        ):
            counts = {
                state: count
                for state, count in session.execute(
                    select(column, func.count()).where(column.in_(allowed)).group_by(column)
                ).all()
            }
            lines.extend(
                (f"# HELP {name} Persisted records by lifecycle state.", f"# TYPE {name} gauge")
            )
            for state in allowed:
                lines.append(f'{name}{{state="{state}"}} {counts.get(state, 0)}')

        latest_queue = (
            select(
                RunEventRecord.run_id.label("run_id"),
                func.max(RunEventRecord.created_at).label("queued_at"),
            )
            .where(RunEventRecord.type == RunEventType.RUN_QUEUED.value)
            .group_by(RunEventRecord.run_id)
            .subquery()
        )
        backlog, oldest_queue = session.execute(
            select(
                func.count(RunRecord.id),
                func.min(func.coalesce(latest_queue.c.queued_at, RunRecord.created_at)),
            )
            .outerjoin(latest_queue, RunRecord.id == latest_queue.c.run_id)
            .where(RunRecord.status == RunStatus.QUEUED.value)
        ).one()
        oldest_approval = session.scalar(
            select(func.min(ApprovalRecord.requested_at)).where(
                ApprovalRecord.status == ApprovalStatus.REQUESTED.value
            )
        )
        gauge("agent_kernel_queue_backlog", "Durable queued runs, not Redis hint count.", backlog)
        gauge(
            "agent_kernel_queue_oldest_wait_seconds",
            "Oldest queued run age since its latest queue event.",
            age(oldest_queue),
        )
        gauge(
            "agent_kernel_approval_oldest_wait_seconds",
            "Oldest unresolved approval age.",
            age(oldest_approval),
        )
        gauge(
            "agent_kernel_operational_snapshot_unixtime",
            "Time of successful persisted-state snapshot.",
            now.timestamp(),
        )
    return "\n".join(lines) + "\n"


try:
    app = create_app()
except Exception:
    # Console-script imports run before main(); do not leak configuration/client
    # exceptions through Python's raw top-level traceback during that import.
    configure_safe_logging()
    logging.getLogger(__name__).exception("API application initialization failed")
    raise SystemExit(1) from None


def main() -> None:
    configure_safe_logging()
    try:
        uvicorn.run(
            "agent_kernel_api.main:app",
            host=api_host_from_env(os.environ),
            port=api_port_from_env(os.environ),
            reload=False,
            log_config=uvicorn_log_config(),
        )
    except Exception:
        logging.getLogger(__name__).exception("API startup failed")
        raise SystemExit(1) from None


def api_host_from_env(env: Mapping[str, str] | None = None) -> str:
    values = env if env is not None else os.environ
    host = values.get("AGENT_KERNEL_API_HOST", "0.0.0.0").strip()
    return host or "0.0.0.0"


def api_port_from_env(env: Mapping[str, str] | None = None) -> int:
    values = env if env is not None else os.environ
    raw_port = values.get("AGENT_KERNEL_API_PORT", "8000").strip()
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("AGENT_KERNEL_API_PORT must be an integer.") from error

    if port < 1 or port > 65535:
        raise ValueError("AGENT_KERNEL_API_PORT must be between 1 and 65535.")
    return port


def _agent_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        workspace_id=agent.workspace_id,
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
        workspace_id=run.workspace_id,
        principal_id=run.principal_id,
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


def _memory_response(memory: MemoryItem) -> MemoryResponse:
    return MemoryResponse(
        id=memory.id,
        workspace_id=memory.workspace_id,
        type=memory.type,
        scope=memory.scope,
        content=memory.content,
        source_run_id=memory.source_run_id,
        confidence=memory.confidence,
        metadata=memory.metadata,
        created_at=memory.created_at,
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
        workspace_id=knowledge_base.workspace_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        status=knowledge_base.status,
        metadata=knowledge_base.metadata,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


def _retrieval_response(response: RagRetrievalResponse) -> RetrievalResponseModel:
    return RetrievalResponseModel(
        knowledge_base_id=response.knowledge_base_id,
        query=response.query,
        model=response.model,
        results=[
            RetrievalResultResponse(
                content=result.content,
                score=result.score,
                citation=CitationResponse(
                    knowledge_base_id=result.citation.knowledge_base_id,
                    document_id=result.citation.document_id,
                    document_title=result.citation.document_title,
                    document_source_uri=result.citation.document_source_uri,
                    chunk_id=result.citation.chunk_id,
                    chunk_index=result.citation.chunk_index,
                    start_char=result.citation.start_char,
                    end_char=result.citation.end_char,
                ),
                metadata=result.metadata,
            )
            for result in response.results
        ],
    )


def _eval_run_response(eval_run: EvalRun) -> EvalRunResponse:
    return EvalRunResponse(
        id=eval_run.id,
        workspace_id=eval_run.workspace_id,
        name=eval_run.name,
        suite_type=eval_run.suite_type,
        status=eval_run.status,
        passed=eval_run.passed,
        case_count=eval_run.case_count,
        passed_count=eval_run.passed_count,
        failed_count=eval_run.failed_count,
        report=eval_run.report,
        error_type=eval_run.error_type,
        error_message=eval_run.error_message,
        trace_id=eval_run.trace_id,
        metadata=eval_run.metadata,
        created_at=eval_run.created_at,
        started_at=eval_run.started_at,
        completed_at=eval_run.completed_at,
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
