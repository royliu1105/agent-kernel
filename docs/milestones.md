# Milestones

## Timeline

The short-term delivery plan is:

```text
Day 1-30: v0.1
Day 31-45: Public Alpha
```

v0.1 should be a deployable, testable, observable, evaluable, resumable Agent runtime foundation.

Public Alpha should be a polished version that an early external user can clone, run, understand, and give feedback on.

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
[~] In progress
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

### Phase 3: Day 14-18 - RAG and Memory

Goal:

```text
Let agents use documents, retrieval, citations, and scoped memory.
```

Checklist:

- [ ] Document model.
- [ ] Document upload.
- [ ] Local object store.
- [ ] Ingestion worker.
- [ ] Text/Markdown parser.
- [ ] Chunker.
- [ ] Embedding interface.
- [ ] OpenAI embeddings.
- [ ] Mock embeddings.
- [ ] pgvector store.
- [ ] Retriever.
- [ ] Citation builder.
- [ ] `kb_search` tool.
- [ ] Short-term memory.
- [ ] Task context.
- [ ] User preferences.
- [ ] Long-term memory.
- [ ] Memory retrieval.

Acceptance:

- [ ] Upload document.
- [ ] Ingest document.
- [ ] Retrieve relevant chunks.
- [ ] Agent calls `kb_search`.
- [ ] Final answer includes citations.
- [ ] Memory can be written, read, scoped, and deleted.

### Phase 4: Day 19-23 - Observability and Evals

Goal:

```text
Make the runtime inspectable, measurable, cost-aware, and regression-testable.
```

Checklist:

- [ ] Structured logs.
- [ ] OpenTelemetry spans.
- [ ] Trace IDs.
- [ ] Model call metrics.
- [ ] Tool call metrics.
- [ ] Retrieval metrics.
- [ ] Cost tracking.
- [ ] Eval dataset format.
- [ ] Eval runner.
- [ ] Assertions.
- [ ] Mock replay provider.
- [ ] Regression report.
- [ ] CI cheap eval.

Acceptance:

- [ ] Every run has a trace ID.
- [ ] Every step has latency data.
- [ ] Model calls record token and cost data.
- [ ] Eval run works through CLI.
- [ ] Failed eval cases produce clear reports.
- [ ] CI runs minimum deterministic evals.

### Phase 5: Day 24-27 - Web UI

Goal:

```text
Create the Agent Workbench UI.
```

Checklist:

- [ ] Dashboard.
- [ ] Agents page.
- [ ] Run timeline.
- [ ] Tool call detail.
- [ ] Approval inbox.
- [ ] Knowledge base page.
- [ ] Eval report page.
- [ ] Settings page.
- [ ] API client.
- [ ] Playwright smoke tests.

Acceptance:

- [ ] User can inspect run timeline.
- [ ] User can approve or reject tool calls.
- [ ] User can inspect document ingestion status.
- [ ] User can view eval reports.
- [ ] Web build passes.

### Phase 6: Day 28-30 - Deployment, Docs, and v0.1 Release

Goal:

```text
Make v0.1 usable by a new developer from a fresh clone.
```

Checklist:

- [ ] Full Docker Compose.
- [ ] `.env.example`.
- [ ] Quickstart.
- [ ] Production config guide.
- [ ] Architecture docs updated.
- [ ] Feature specs updated.
- [ ] Examples.
- [ ] CONTRIBUTING.
- [ ] SECURITY.
- [ ] ROADMAP.
- [ ] Release checklist.
- [ ] v0.1.0 release notes.

Acceptance:

- [ ] Fresh clone can run quickstart.
- [ ] CI is green.
- [ ] Docker Compose starts full stack.
- [ ] Examples work.
- [ ] Docs explain architecture, usage, tradeoffs, and next steps.

## Public Alpha: Day 31-45

Goal:

```text
Turn v0.1 into a polished early-user release.
```

Checklist:

- [ ] Fix v0.1 bugs.
- [ ] Improve quickstart.
- [ ] Improve examples.
- [ ] Improve Web UI polish.
- [ ] Add missing tests around fragile paths.
- [ ] Expand behavior eval coverage.
- [ ] Improve error messages.
- [ ] Harden Docker Compose startup.
- [ ] Add troubleshooting docs.
- [ ] Add first external-user feedback loop.
- [ ] Prepare Public Alpha announcement.

Acceptance:

- [ ] A new user can run the project without maintainer help.
- [ ] Core examples work end to end.
- [ ] Known limitations are documented.
- [ ] Public Alpha release notes are clear.
- [ ] Feedback channels are documented.

## Rule for Updating This File

Update this file when:

- A phase starts.
- A phase completes.
- A milestone changes.
- A scope decision is made.
- A blocker affects delivery.

Do not use this file for detailed task logs. Detailed implementation notes belong in PRs, issues, or phase-specific planning docs.
