# Module Boundaries

## Package Overview

```text
packages/kernel-core
packages/kernel-identity
packages/kernel-runtime
packages/kernel-providers
packages/kernel-tools
packages/kernel-memory
packages/kernel-rag
packages/kernel-policy
packages/kernel-evals
packages/kernel-observability
packages/kernel-storage
```

## kernel-core

Stable domain models, interfaces, errors, events, and enums.

Domain entities:

- Agent.
- Run.
- RunStep.
- Message.
- ToolCall.
- Approval.
- Prompt.
- MemoryItem.
- Document.
- DocumentChunk.
- EvalDataset.
- EvalCase.
- EvalRun.

Core interfaces:

- `LLMProvider`
- `Tool`
- `ToolRegistry`
- `RunStore`
- `MemoryStore`
- `VectorStore`
- `ObjectStore`
- `Queue`
- `PolicyEngine`
- `Tracer`

This package must stay infrastructure-free.

## kernel-identity

Identity, workspace, and RBAC primitives:

- Principal.
- Workspace.
- WorkspaceMembership.
- Built-in workspace roles.
- Fine-grained permissions.
- Authorization requests.
- Authorization decisions.
- Workspace-scoped authorizer.

This package must stay infrastructure-free. API authentication middleware,
identity persistence, API keys, browser sessions, OIDC, and SSO are added in
later Beta slices.

## kernel-runtime

Agent execution core:

- Agent loop.
- Planner.
- Executor.
- Run state machine.
- Workflow graph.
- Interrupt/resume.
- Retry/fallback.
- Cost accounting.
- Trace spans.

## kernel-providers

LLM provider integrations:

- OpenAI provider.
- Mock provider.
- Replay provider.
- Model router.
- Token and cost model.

## kernel-tools

Tool system:

- Tool registry.
- Tool schema.
- Tool executor.
- Input/output validation.
- Risk levels.
- Timeout/retry.
- Built-in tools.

## kernel-policy

Security and permission policy:

- Permission checks.
- Tool allow/deny/approval decisions.
- Risk-level evaluation.
- Secret redaction.
- Audit events.

## kernel-rag

Knowledge base and retrieval:

- Document metadata.
- Parsers.
- Chunkers.
- Embedding providers.
- Vector store adapters.
- Retriever.
- Citation builder.
- RAG tool.
- Ingestion jobs.

## kernel-memory

Memory system:

- Short-term context.
- Task context.
- User preference store.
- Long-term memory.
- Memory retrieval.
- Memory write policy.

## kernel-evals

Evaluation system:

- Dataset format.
- Eval runner.
- Assertions.
- Mock replay.
- Regression report.
- CI eval.

## kernel-observability

Runtime visibility:

- Structured logs.
- OpenTelemetry traces.
- Metrics.
- Cost tracking.
- Latency tracking.
- Run summary.

## kernel-storage

Persistence and infrastructure adapters:

- SQLAlchemy models.
- Alembic migrations.
- Repositories.
- Postgres.
- pgvector.
- Local object storage.
- S3/MinIO-compatible object storage.
- Redis queue implementation.

## Application Entrypoints

### apps/api

FastAPI app:

- HTTP validation.
- Authentication.
- Calls service/runtime layer.
- Does not run long agent loops directly.

### apps/worker

Worker process:

- Pulls jobs.
- Loads run state.
- Calls runtime.
- Persists step/tool/model/retry results.

### apps/cli

Typer CLI:

- Developer entrypoint.
- Calls local API by default.
- Can later support local direct mode.

### apps/web

Next.js Web UI:

- Dashboard.
- Agent configuration.
- Run timeline.
- Approval inbox.
- Knowledge base.
- Eval reports.

The Web UI never accesses the database directly.
