# Development Plan

## Delivery Target

The original v0.1 target is complete and published:

```text
Day 1-38: v0.1.0 foundation, release hardening, tag, CI verification, and GitHub Release
```

The next target is Public Alpha and then v1.0:

```text
Day 39-51: Public Alpha hardening
Day 52-75: Beta production hardening
Day 76-90: v1.0 release candidate and final release work
```

The v1.0 version should be stable, deployable, testable, recoverable,
observable, evaluable, secure enough for serious self-hosted use, and
documented with upgrade and operational guidance.

See [Post-v0.1 Completion Plan](post-v0.1-plan.md) for the canonical
post-v0.1 plan.

## Development Method

Use:

```text
Production-grade skeleton first
Vertical slices
Daily acceptance criteria
Tests and docs alongside code
```

For every core feature:

1. Write or update a lightweight spec or ADR.
2. Define domain models.
3. Define interfaces.
4. Implement the minimal production-shaped version.
5. Add unit tests.
6. Add integration tests.
7. Expose through CLI and/or API.
8. Add observability.
9. Update docs and examples.
10. Verify acceptance criteria.

## Phase 0: Day 1

Goal: project skeleton and engineering baseline.

Deliverables:

- Repo skeleton.
- API, CLI, worker, and Web minimal startup.
- Docker Compose.
- CI.
- README.
- Initial ADRs.
- Basic tests.

Acceptance:

- API starts.
- CLI prints version.
- Worker starts.
- Web starts.
- Tests pass.
- Lint and typecheck pass.

## Phase 1: Day 2-7 Core Runtime

Deliverables:

- Domain models.
- Postgres schema.
- Alembic migrations.
- Repository layer.
- `LLMProvider`.
- OpenAI provider.
- Mock provider.
- Model router.
- Prompt versioning.
- Run state machine.
- Agent loop.
- Run event stream.
- CLI/API run operations.

Acceptance:

- Create agent -> create run -> worker executes -> final output persisted.
- Mock provider deterministic tests pass.
- OpenAI smoke path is documented.
- Run timeline is persisted.

## Phase 2: Day 8-13 Tools, Policy, Approval, Retry, and Fallback

Deliverables:

- Tool interface.
- Tool registry.
- JSON schema validation.
- Tool executor.
- Risk levels.
- Policy engine.
- Approval API and CLI.
- Interrupt/resume.
- Retry/fallback.
- Built-in tools.
- Audit log.

Acceptance:

- Safe tool auto-executes.
- Risky tool pauses run.
- Approval resumes run.
- Rejection stops safely.
- Tool failure retries.
- Audit log is complete.

## Phase 3: Day 14-24 RAG Retrieval, Agent Integration, and Memory

Phase 3 is realigned in [Phase 3 Realignment](phase-3-realignment.md).

### Phase 3A: Day 14-18 RAG Ingestion and Indexing Foundation

Status:

```text
Complete
```

Deliverables completed:

- Document model.
- Document upload.
- Local object store.
- Ingestion job model.
- Manual ingestion API and CLI.
- Text/Markdown parser.
- Chunker.
- Embedding interface.
- Mock embeddings.
- Vector store foundation.

Acceptance:

- Upload document.
- Ingest and parse document.
- Chunk parsed document.
- Index chunks with deterministic mock embeddings.
- Persist chunk embeddings.

### Phase 3B: Day 19-21 RAG Retrieval and Agent Integration

Status:

```text
Complete
```

Deliverables:

- Retriever.
- Citation builder.
- Retrieval API and CLI.
- `kb_search` tool.
- Agent runtime RAG integration.
- RAG behavior evals.
- RAG regression cases.

Acceptance:

- Query can retrieve relevant chunks.
- Retrieval response includes citations.
- Agent can call `kb_search`.
- RAG behavior has deterministic regression tests.

### Phase 3C: Day 22-23 Memory Foundation

Status:

```text
Complete
```

Deliverables:

- Short-term memory.
- Task context.
- User preferences.
- Long-term memory.
- Memory retrieval.
- Memory API and CLI.
- Agent memory context integration.

Acceptance:

- Memory can be written and read.
- Memory is scoped and inspectable.
- Agent can use retrieved memory context.

### Phase 3 Closure: Day 24

Status:

```text
Complete
```

Deliverables:

- Phase 3 summary.
- Updated RAG and memory specs.
- Updated milestones.
- Full verification.
- Known limitations documented.

Acceptance:

- Upload document -> ingest -> chunk -> index -> retrieve.
- Agent calls `kb_search`.
- Answer includes citations.
- Memory can be written, retrieved, and used as scoped context.
- RAG and memory tests pass.

## Phase 4: Day 25-29 Observability and Evals

Deliverables:

- Structured logs.
- OpenTelemetry spans.
- Trace IDs.
- Model/tool/retrieval metrics.
- Cost tracking.
- Eval dataset format.
- Eval runner.
- Assertions.
- Mock replay provider.
- Regression report.
- CI cheap eval.

Acceptance:

- Every run has a trace ID.
- Every step has latency and cost data.
- Eval run works through CLI.
- Failed cases generate reports.
- CI runs minimum evals.

## Phase 5: Day 30-33 Web UI

Deliverables:

- Dashboard.
- Agents page.
- Run timeline.
- Tool call detail.
- Approval inbox.
- Knowledge base page.
- Eval report page.
- Settings.
- Playwright smoke tests.

Acceptance:

- User can inspect a run timeline.
- User can approve or reject tool calls.
- User can inspect document ingestion status.
- User can view eval reports.
- Web build passes.

## Phase 6: Day 34-38 Deployment, Docs, and Release

Status:

```text
Complete
```

Deliverables:

- Full Docker Compose.
- `.env.example`.
- Production config guide.
- Quickstart.
- Architecture docs.
- Feature specs.
- Examples.
- CONTRIBUTING.
- SECURITY.
- ROADMAP.
- Release checklist.
- v0.1.0 plan.
- Fresh-run release hardening fixes.
- Dependency audit review.
- GitHub CI trigger fix.
- Annotated `v0.1.0` tag.
- GitHub Release.

Acceptance:

- [x] Fresh clone can run the quickstart.
- [x] CI is green.
- [x] Docker Compose starts the full stack.
- [x] Examples work.
- [x] Docs explain architecture and tradeoffs.

## Stage 7: Day 39-51 Public Alpha Hardening

Status: complete.

Goal: make the published v0.1.0 foundation easy for early external users to
try, understand, and critique.

Deliverables:

- Public feedback channels.
- GitHub issue templates.
- README and quickstart polish.
- More examples.
- Live Web API integration for the highest-value Workbench workflows.
- Expanded behavior evals.
- Better runtime and setup error messages.
- Dependency audit follow-up.
- Public Alpha notes or announcement.

Acceptance:

- [x] New user can follow README and quickstart without maintainer help.
- [x] Full Compose startup is verified from a clean checkout.
- [x] Core examples are easy to discover and run.
- [x] GitHub CI is green.
- [x] Public feedback path is documented.

Summary: [Public Alpha Summary](public-alpha-summary.md).

## Stage 8: Day 52-75 Beta Production Hardening

Goal: make Agent Kernel credible for internal production pilots and serious
extension by other developers.

Deliverables:

- Auth baseline.
- RBAC baseline.
- Tenant or workspace scoping.
- Provider-native function calling.
- Durable model/tool/model execution loop.
- Persisted tool-call records.
- Redis-backed durable queue.
- Worker leases and stuck-run recovery.
- OpenTelemetry exporters.
- Prometheus-compatible metrics endpoint.
- S3/MinIO object storage backend.
- OpenAI embeddings backend.
- pgvector-native vector store.
- Persisted eval runs and eval API.
- Live Web Workbench integration for core operations.
- SQLite and Postgres migration tests.

Daily execution map:

```text
Day 52: Identity, workspace, and RBAC domain foundation
Day 53: Identity persistence and API key storage foundation
Day 54: API key authentication middleware
Day 55: Route-level authorization baseline
Day 56: Workspace scope retrofit plan and first scoped resources
Day 57: Approval authorization enforcement
Day 58: Auth/RBAC docs and security test closure
Day 59: Worker lease model and storage foundation
Day 60: Stuck-run detection and recovery
Day 61: Redis queue adapter foundation
Day 62: Durable retry visibility and worker restart tests
Day 63: Durable execution closure
Day 64: Provider-native tool-call adapter contract
Day 65: OpenAI native tool-call parsing and persistence
Day 66: Model/tool/model execution loop
Day 67: Provider-native tool-call evals and regression tests
Day 68: OpenAI embeddings backend
Day 69: pgvector-native vector store
Day 70: S3/MinIO object storage backend
Day 71: Production RAG/storage integration tests
Day 72: OpenTelemetry exporter configuration
Day 73: Prometheus-compatible metrics endpoint
Day 74: Persisted eval runs, eval API, and live Web operator views
Day 75: Beta closure, summary docs, and full verification
```

Acceptance:

- [ ] Runtime execution survives worker restarts.
- [ ] Tool calls and approvals are durable and inspectable.
- [ ] Security boundaries are explicit and tested.
- [ ] Telemetry can be exported to common production tools.
- [ ] RAG can run with real embeddings and pgvector.
- [ ] Storage backends can be switched by configuration.

## Stage 9: Day 76-90 v1.0 Release Candidate

Goal: freeze the stable production contract and remove release surprises.

Deliverables:

- Public API and CLI compatibility policy.
- Upgrade and migration policy.
- Versioned configuration docs.
- Backup and restore guidance.
- Security hardening checklist.
- Load and soak test scenarios.
- Release-blocking eval suites.
- Full release smoke tests.
- v1.0 release checklist.
- v1.0 release notes.
- Clean-machine release rehearsal.

Acceptance:

- [ ] Stable API and CLI contract is documented.
- [ ] Clean-machine release rehearsal passes.
- [ ] Critical paths pass automated tests and evals.
- [ ] Known limitations are acceptable for v1.0.
- [ ] v1.0 docs match actual behavior.

## Daily Start Workflow

Do not keep adding every daily prompt to this file. This document is the phase-level development plan.

Daily execution checklists live in:

```text
docs/daily/day-XX.md
```

At the start of each development day:

1. Create or update the corresponding daily plan.
2. Read the relevant specs and milestone section.
3. Use the daily plan as the execution checklist.
4. Update daily checkboxes as work completes.
5. Update `docs/milestones.md` when phase-level progress changes.
6. Update specs or ADRs if implementation changes behavior or decisions.

Daily files should be created just-in-time. Do not pre-create all planned
future days.

## Generic Daily Start Prompt

Use this prompt pattern to begin a development day:

```text
开始 Day N：请按照 docs/daily/day-NN.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取当天 daily plan、相关 specs 和 docs/milestones.md。
- 只实现当天 scope 内的内容，不提前做后续阶段。
- 如果行为或架构决策变化，更新对应 spec 或 ADR。
- 完成后运行当天 plan 中的 verification commands。
- 更新 docs/daily/day-NN.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

For example, Day 2 should use:

```text
开始 Day 2：请按照 docs/daily/day-02.md 执行今天的计划。
```
