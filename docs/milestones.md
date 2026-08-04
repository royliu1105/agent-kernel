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
- [ ] OpenAI embeddings.
- [x] Mock embeddings.
- [x] Vector store foundation.
- [ ] pgvector-native store.

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
[~] In progress
```

Checklist:

- [x] Create public feedback channels.
- [x] Add issue templates.
- [x] Improve README first-run path.
- [x] Improve quickstart from first-user perspective.
- [x] Improve examples.
- [ ] Improve Web UI polish.
- [ ] Replace key fixture-backed Web views with live API integration.
- [x] Document first live Web API integration priorities.
- [x] Implement first live Web API health integration.
- [x] Implement live run detail and timeline lookup.
- [x] Implement live approval inbox status integration.
- [x] Implement live approval approve/reject mutation UI.
- [x] Implement live knowledge base list integration.
- [x] Add missing tests around fragile paths.
- [x] Expand behavior eval coverage.
- [ ] Improve error messages.
- [x] Harden Docker Compose startup.
- [x] Add troubleshooting docs.
- [x] Add first external-user feedback loop.
- [ ] Prepare Public Alpha announcement.

Acceptance:

- [x] A new user can run the project without maintainer help.
- [x] Core examples work end to end.
- [x] Known limitations are documented.
- [ ] Public Alpha release notes are clear.
- [x] Feedback channels are documented.

## Beta: Day 52-75

Goal:

```text
Make Agent Kernel credible for internal production pilots and serious extension
by other developers.
```

Status:

```text
[ ] Not started
```

Checklist:

- [ ] Authentication baseline.
- [ ] Authorization/RBAC baseline.
- [ ] Tenant or workspace scoping model.
- [ ] Provider-native function calling.
- [ ] Durable model/tool/model execution loop.
- [ ] Persisted tool-call records.
- [ ] Redis-backed durable queue.
- [ ] Worker leasing and stuck-run recovery.
- [ ] OpenTelemetry exporter configuration.
- [ ] Prometheus-compatible metrics endpoint.
- [ ] S3/MinIO object storage backend.
- [ ] OpenAI embeddings backend.
- [ ] pgvector-native vector store.
- [ ] Persisted eval runs.
- [ ] Eval API.
- [ ] Live Web Workbench integration for core operator workflows.
- [ ] SQLite and Postgres migration tests.

Acceptance:

- [ ] Runtime execution survives worker restarts.
- [ ] Tool calls and approvals are durable and inspectable.
- [ ] Security boundaries are explicit and tested.
- [ ] Telemetry can be exported to common production tools.
- [ ] RAG can run with real embeddings and pgvector.
- [ ] Storage backends can be switched by configuration.

## v1.0 Release Candidate: Day 76-90

Goal:

```text
Freeze the stable production contract and remove surprises before v1.0.
```

Status:

```text
[ ] Not started
```

Checklist:

- [ ] Public API and CLI compatibility policy.
- [ ] Upgrade and migration policy.
- [ ] Versioned configuration documentation.
- [ ] Backup and restore guidance.
- [ ] Security hardening checklist.
- [ ] Load and soak test scenarios.
- [ ] Release-blocking eval suites.
- [ ] Full release smoke tests.
- [ ] v1.0 release checklist.
- [ ] v1.0 release notes.
- [ ] Clean-machine release rehearsal.

Acceptance:

- [ ] Stable API and CLI contract is documented.
- [ ] Clean-machine release rehearsal passes.
- [ ] Critical paths pass automated tests and evals.
- [ ] Known limitations are acceptable for v1.0.
- [ ] v1.0 docs match actual behavior.

## Rule for Updating This File

Update this file when:

- A phase starts.
- A phase completes.
- A milestone changes.
- A scope decision is made.
- A blocker affects delivery.

Do not use this file for detailed task logs. Detailed implementation notes belong in PRs, issues, or phase-specific planning docs.
