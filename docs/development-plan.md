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

## Phase 3: Day 14-18 RAG and Memory

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

Daily files should be created just-in-time. Do not pre-create all 45 days.

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
