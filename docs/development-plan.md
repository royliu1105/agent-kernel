# Development Plan

## Delivery Target

The target is not reduced. The timeline is compressed through daily execution:

```text
30 days to v0.1
45 days to Public Alpha
```

The v0.1 version should be deployable, testable, recoverable, observable, evaluable, and documented.

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

## Phase 2: Day 8-12 Tools, Policy, and Approval

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

## Phase 3: Day 13-18 RAG and Memory

Deliverables:

- Document model.
- Document upload.
- Local object store.
- Ingestion worker.
- Text/Markdown parser.
- Chunker.
- Embedding interface.
- OpenAI embeddings.
- Mock embeddings.
- pgvector store.
- Retriever.
- Citation builder.
- RAG tool.
- Short-term memory.
- Task context.
- User preferences.
- Long-term memory.
- Memory retrieval.

Acceptance:

- Upload document -> ingest -> retrieve.
- Agent calls `kb_search`.
- Answer includes citations.
- Memory can be written and read.
- RAG and memory tests pass.

## Phase 4: Day 19-23 Observability and Evals

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

## Phase 5: Day 24-27 Web UI

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

## Phase 6: Day 28-30 Deployment, Docs, and Release

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

Acceptance:

- Fresh clone can run the quickstart.
- CI is green.
- Docker Compose starts the full stack.
- Examples work.
- Docs explain architecture and tradeoffs.

## Day 1 Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 1：请在当前仓库创建 Agent Kernel 的项目骨架和工程基线。

要求：
- 先检查当前仓库状态，不要覆盖已有用户文件。
- 创建 monorepo 结构。
- 后端使用 Python 3.12、FastAPI、Pydantic v2、SQLAlchemy、Alembic、Typer、pytest、ruff、mypy。
- 前端创建 Next.js + TypeScript 最小 app。
- 添加 API /healthz。
- 添加 CLI agent-kernel --version。
- 添加 worker 启动入口。
- 添加 kernel-core 中的基础 domain models：Agent、Run、RunStep、ToolCall、Approval。
- 添加 docker-compose.yml，包含 Postgres + pgvector + Redis。
- 添加 .env.example。
- 添加 GitHub Actions CI。
- 添加 README、CONTRIBUTING、SECURITY、ROADMAP、docs/architecture.md、docs/adr/0001-modular-monolith.md、docs/adr/0002-storage.md、docs/adr/0003-python-runtime.md。
- 添加基础测试。
- 完成后运行 ruff、mypy、pytest；如果 Web app 建好了，也运行 npm lint/build。
- 最后总结文件结构、启动方式和验证结果。
```
