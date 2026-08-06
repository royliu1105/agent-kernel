# Milestones

## Timeline

The short-term delivery plan is:

```text
Day 1-38: v0.1.0 published release
Day 39-51: Public Alpha
Day 52-75: Beta production hardening
Day 76-90: v1.0 release candidate and release work
```

v0.1.0 is a deployable, testable, observable, evaluable, resumable Agent runtime foundation.

Public Alpha should be a polished version that an early external user can clone, run, understand, and give feedback on.

Beta should add the production hardening expected for serious self-hosted pilots.

v1.0 should freeze a stable self-hosted runtime contract.

## Progress Legend

Use these markers when updating progress:

```text
[ ] Not started
[~] In progress
[x] Done
[!] Blocked or needs decision
```

## v0.1: Day 1-30

### Phase 0: Day 1 - Project Skeleton and Engineering Baseline

Goal:

```text
Turn the repository into a serious open-source project skeleton.
```

Checklist:

- [x] Monorepo directory structure.
- [x] Python project configuration.
- [x] API minimal startup.
- [x] CLI minimal startup.
- [x] Worker minimal startup.
- [x] Web minimal startup.
- [x] Docker Compose for Postgres/pgvector and Redis.
- [x] `.env.example`.
- [x] `.gitignore`.
- [x] GitHub Actions CI.
- [x] Basic tests.
- [x] README updated.
- [x] Initial quality commands pass where possible.

Acceptance:

- [x] `uv sync` works.
- [x] `agent-kernel --version` works.
- [x] API `/healthz` works.
- [x] Worker starts.
- [x] Web app builds or starts.
- [x] `uv run pytest` passes.
- [x] `uv run ruff check .` passes.
- [x] `uv run mypy .` passes.

### Phase 1: Day 2-7 - Core Runtime

Status:

```text
[x] Done
```

Goal:

```text
Create the first real agent run lifecycle.
```

Checklist:

- [x] Domain models.
- [x] Postgres schema.
- [x] Alembic migrations.
- [x] Repository layer.
- [x] `LLMProvider` interface.
- [x] OpenAI provider.
- [x] Mock provider.
- [x] Replay provider baseline.
- [x] Model router.
- [x] Prompt versioning.
- [x] Run state machine.
- [x] Agent loop.
- [x] Run event stream.
- [x] API run endpoints.
- [x] CLI run commands.

Acceptance:

- [x] Create agent.
- [x] Create run.
- [x] Worker executes run.
- [x] Final output is persisted.
- [x] Timeline is persisted.
- [x] Mock provider deterministic tests pass.
- [x] OpenAI smoke path is documented.

### Phase 2: Day 8-13 - Tools, Policy, Approval, Retry, and Fallback

Goal:

```text
Let agents call tools safely with policy checks and human approval.
```

Checklist:

- [x] Tool interface.
- [x] Tool registry.
- [x] JSON schema validation.
- [x] Tool executor.
- [x] Built-in safe tools.
- [x] Risk levels.
- [x] Policy engine.
- [x] Approval model.
- [x] Approval API.
- [x] Approval CLI.
- [x] Interrupt/resume.
- [x] Retry/fallback.
- [x] Audit log.

Acceptance:

- [x] Safe tool auto-executes.
- [x] Risky tool pauses run.
- [x] Approval resumes run.
- [x] Rejection stops safely.
- [x] Tool failure retries where safe.
- [x] Tool calls and decisions are auditable.

### Phase 3: Day 14-24 - RAG Retrieval, Agent Integration, and Memory

Goal:

```text
Let agents use documents, retrieval, citations, and scoped memory.
```

Plan:

```text
Phase 3A: Day 14-18 - RAG Ingestion + Indexing Foundation
Phase 3B: Day 19-21 - RAG Retrieval + Agent Integration
Phase 3C: Day 22-23 - Memory Foundation
Phase 3 Closure: Day 24
```

Checklist:

#### Phase 3A: RAG Ingestion + Indexing Foundation

- [x] Knowledge base model.
- [x] Document model.
- [x] Knowledge base and document metadata storage.
- [x] Knowledge base and document metadata API.
- [x] Knowledge base and document metadata CLI.
- [x] Document upload.
- [x] Local object store.
- [x] Ingestion job model and storage.
- [x] Manual ingestion API and CLI.
- [ ] Ingestion worker.
- [x] Text/Markdown parser.
- [x] Chunker.
- [x] Document chunk storage.
- [x] Embedding interface.
- [x] OpenAI embeddings.
- [x] Mock embeddings.
- [x] Vector store foundation.
- [x] pgvector-native store.

#### Phase 3B: RAG Retrieval + Agent Integration

- [x] Retriever.
- [x] Citation builder.
- [x] Retrieval API.
- [x] Retrieval CLI.
- [x] `kb_search` tool.
- [x] Agent runtime RAG integration.
- [x] RAG behavior evals.
- [x] RAG regression cases.

#### Phase 3C: Memory Foundation

- [x] Short-term memory.
- [x] Task context.
- [x] User preferences.
- [x] Long-term memory.
- [x] Memory retrieval.
- [x] Memory API.
- [x] Memory CLI.
- [x] Agent memory context integration.

#### Phase 3 Closure

- [x] Phase 3 summary.
- [x] RAG spec updated.
- [x] Memory spec updated.
- [x] Known limitations documented.
- [x] Full verification.

Acceptance:

- [x] Upload document.
- [x] Ingest document.
- [x] Chunk document.
- [x] Index document with mock embeddings.
- [x] Retrieve relevant chunks.
- [x] Agent calls `kb_search`.
- [ ] Final answer includes citations.
- [x] Memory can be written, read, scoped, and deleted.

### Phase 4: Day 25-29 - Observability and Evals

Goal:

```text
Make the runtime inspectable, measurable, cost-aware, and regression-testable.
```

Checklist:

- [x] Structured logs.
- [ ] OpenTelemetry spans.
- [x] Trace IDs.
- [x] Model call metrics.
- [x] Tool call metrics.
- [x] Retrieval metrics.
- [ ] Cost tracking.
- [x] Eval dataset format.
- [x] Eval runner.
- [x] Assertions.
- [ ] Mock replay provider.
- [x] Regression report.
- [x] CI cheap eval.

Acceptance:

- [x] Every run has a trace ID.
- [ ] Every step has latency data.
- [x] Model calls record token and cost data.
- [x] Eval run works through CLI.
- [x] Failed eval cases produce clear reports.
- [x] CI runs minimum deterministic evals.

### Phase 5: Day 30-33 - Web UI

Goal:

```text
Create the Agent Workbench UI.
```

Checklist:

- [x] Dashboard.
- [x] Agents page.
- [x] Run timeline.
- [x] Tool call detail.
- [x] Approval inbox.
- [x] Knowledge base page.
- [x] Eval report page.
- [x] Settings page.
- [x] API client.
- [x] Playwright smoke tests.
- [x] Live retrieval search integration.

Acceptance:

- [x] User can inspect run timeline.
- [x] User can approve or reject tool calls.
- [x] User can inspect document ingestion status.
- [x] User can view eval reports.
- [x] Web build passes.

### Phase 6: Day 34-38 - Deployment, Docs, and v0.1 Release

Goal:

```text
Make v0.1 usable by a new developer from a fresh clone.
```

Status:

```text
[x] Done
```

Checklist:

- [x] Full Docker Compose.
- [x] `.env.example`.
- [x] Quickstart.
- [x] Production config guide.
- [x] Architecture docs updated.
- [x] Feature specs updated.
- [x] Examples.
- [x] CONTRIBUTING.
- [x] SECURITY.
- [x] ROADMAP.
- [x] Release checklist.
- [x] v0.1.0 release notes.
- [x] Fresh-run backend quickstart hardening.
- [x] Fresh-run Web install verification.
- [x] Docker Compose full-stack verification.
- [x] GitHub CI trigger fix and remote green run.
- [x] Annotated `v0.1.0` tag.
- [x] GitHub Release.

Acceptance:

- [x] Fresh clone can run quickstart.
- [x] CI is green.
- [x] Docker Compose starts full stack.
- [x] Examples work.
- [x] Docs explain architecture, usage, tradeoffs, and next steps.

## Public Alpha: Day 39-51

Goal:

```text
Turn v0.1 into a polished early-user release.
```

Status:

```text
[x] Complete
```

Checklist:

- [x] Create public feedback channels.
- [x] Add issue templates.
- [x] Improve README first-run path.
- [x] Improve quickstart from first-user perspective.
- [x] Improve examples.
- [x] Improve Web UI polish.
- [x] Replace key backend-supported fixture-backed Web paths with live API integration.
- [x] Document first live Web API integration priorities.
- [x] Implement first live Web API health integration.
- [x] Implement live run detail and timeline lookup.
- [x] Implement live approval inbox status integration.
- [x] Implement live approval approve/reject mutation UI.
- [x] Implement live knowledge base list integration.
- [x] Add missing tests around fragile paths.
- [x] Expand behavior eval coverage.
- [x] Improve error messages.
- [x] Harden Docker Compose startup.
- [x] Add troubleshooting docs.
- [x] Add first external-user feedback loop.
- [x] Prepare Public Alpha announcement.

Acceptance:

- [x] A new user can run the project without maintainer help.
- [x] Core examples work end to end.
- [x] Known limitations are documented.
- [x] Public Alpha release notes are clear.
- [x] Feedback channels are documented.

Closure notes:

- Key live Web API paths are complete for health, run lookup, timeline,
  approvals, approval mutations, knowledge base list, and retrieval search.
- Remaining preview-backed Workbench areas are documented as Beta/v1.0 follow-up
  work rather than Public Alpha blockers.
- See [Public Alpha Summary](public-alpha-summary.md).

## Beta: Day 52-75

Goal:

```text
Make Agent Kernel credible for internal production pilots and serious extension
by other developers.
```

Status:

```text
[x] Complete
```

Checklist:

- [x] API key authentication middleware.
- [x] Route-level authorization baseline.
- [x] Authorization/RBAC domain baseline.
- [x] Workspace scoping domain model.
- [x] Agent and run workspace scope retrofit.
- [x] Approval authorization enforcement.
- [x] Identity persistence and API key storage foundation.
- [x] Auth/RBAC docs and security test closure.
- [x] Provider-native function calling.
- [x] Durable model/tool/model execution loop.
- [x] Persisted tool-call records.
- [x] Redis-backed queue adapter foundation.
- [x] Worker leasing and stuck-run recovery.
- [x] OpenTelemetry exporter configuration.
- [x] Prometheus-compatible metrics endpoint.
- [x] S3/MinIO object storage backend.
- [x] OpenAI embeddings backend.
- [x] pgvector-native vector store.
- [x] Persisted eval runs.
- [x] Eval API.
- [x] Live Web Workbench integration for core operator workflows.
- [x] SQLite and Postgres migration smoke tests.

Daily execution map:

- [x] Day 52: Identity, workspace, and RBAC domain foundation.
- [x] Day 53: Identity persistence and API key storage foundation.
- [x] Day 54: API key authentication middleware.
- [x] Day 55: Route-level authorization baseline.
- [x] Day 56: Workspace scope retrofit plan and first scoped resources.
- [x] Day 57: Approval authorization enforcement.
- [x] Day 58: Auth/RBAC docs and security test closure.
- [x] Day 59: Worker lease model and storage foundation.
- [x] Day 60: Stuck-run detection and recovery.
- [x] Day 61: Redis queue adapter foundation.
- [x] Day 62: Durable retry visibility and worker restart tests.
- [x] Day 63: Durable execution closure.
- [x] Day 64: Provider-native tool-call adapter contract.
- [x] Day 65: OpenAI native tool-call parsing and persistence.
- [x] Day 66: Model/tool/model execution loop.
- [x] Day 67: Provider-native tool-call evals and regression tests.
- [x] Day 68: OpenAI embeddings backend.
- [x] Day 69: pgvector-native vector store.
- [x] Day 70: S3/MinIO object storage backend.
- [x] Day 71: Production RAG/storage integration tests.
- [x] Day 72: OpenTelemetry exporter configuration.
- [x] Day 73: Prometheus-compatible metrics endpoint.
- [x] Day 74: Persisted eval runs, eval API, and live Web operator views.
- [x] Day 75: Beta closure, summary docs, and full verification.

Acceptance:

- [x] Runtime execution survives worker restarts.
- [x] Tool calls and approvals are durable and inspectable.
- [x] Security boundaries are explicit and tested.
- [x] Telemetry can be exported to common production tools.
- [x] RAG can run with real embeddings and pgvector.
- [x] Storage backends can be switched by configuration.

Closure notes:

- See [Beta Summary](beta-summary.md).
- Redis is complete as a queue adapter foundation and coordination port. The
  default worker loop remains database-first and Redis-first scheduling is a
  v1.0 RC hardening follow-up.
- Migration compatibility is covered by a SQLite upgrade regression test and
  GitHub CI SQLite/Postgres migration smoke checks.

## v1.0 Release Candidate: Day 76-90

Goal:

```text
Freeze the stable production contract and remove surprises before v1.0.
```

Status:

```text
[~] In progress
```

Checklist:

- [x] Public API and CLI compatibility policy.
- [x] Upgrade and migration policy.
- [x] Versioned configuration documentation.
- [x] Backup and restore guidance.
- [x] Security hardening checklist.
- [x] Load and soak test scenarios.
- [x] Release-blocking eval suites.
- [x] Full release smoke tests.
- [ ] v1.0 release checklist.
- [ ] v1.0 release notes.
- [ ] Clean-machine release rehearsal.

Acceptance:

- [x] Stable API and CLI contract is documented.
- [ ] Clean-machine release rehearsal passes.
- [x] Critical paths pass automated tests and evals.
- [ ] Known limitations are acceptable for v1.0.
- [ ] v1.0 docs match actual behavior.

Daily execution map:

- [x] Day 76: API/CLI contract audit and compatibility policy.
- [x] Day 77: Versioned configuration documentation.
- [x] Day 78: Upgrade and migration policy.
- [x] Day 79: Backup and restore guidance.
- [x] Day 80: Security hardening checklist.
- [x] Day 81: Release-blocking eval suite definition.
- [x] Day 82: Full release smoke test matrix.
- [x] Day 83: Load and soak test scenarios.
- [x] Day 84: Clean-machine release rehearsal plan.
- [x] Day 85: Clean-machine release rehearsal fixes.
- [ ] Day 86: v1.0 docs consistency audit.
- [ ] Day 87: Known limitations review and scope freeze.
- [ ] Day 88: v1.0 release checklist.
- [ ] Day 89: v1.0 release notes.
- [ ] Day 90: v1.0 final verification and release readiness.

## Rule for Updating This File

Update this file when:

- A phase starts.
- A phase completes.
- A milestone changes.
- A scope decision is made.
- A blocker affects delivery.

Do not use this file for detailed task logs. Detailed implementation notes belong in PRs, issues, or phase-specific planning docs.
