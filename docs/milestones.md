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

- [ ] Monorepo directory structure.
- [ ] Python project configuration.
- [ ] API minimal startup.
- [ ] CLI minimal startup.
- [ ] Worker minimal startup.
- [ ] Web minimal startup.
- [ ] Docker Compose for Postgres/pgvector and Redis.
- [ ] `.env.example`.
- [ ] `.gitignore`.
- [ ] GitHub Actions CI.
- [ ] Basic tests.
- [ ] README updated.
- [ ] Initial quality commands pass where possible.

Acceptance:

- [ ] `uv sync` works.
- [ ] `agent-kernel --version` works.
- [ ] API `/healthz` works.
- [ ] Worker starts.
- [ ] Web app builds or starts.
- [ ] `uv run pytest` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy .` passes.

### Phase 1: Day 2-7 - Core Runtime

Goal:

```text
Create the first real agent run lifecycle.
```

Checklist:

- [ ] Domain models.
- [ ] Postgres schema.
- [ ] Alembic migrations.
- [ ] Repository layer.
- [ ] `LLMProvider` interface.
- [ ] OpenAI provider.
- [ ] Mock provider.
- [ ] Replay provider baseline.
- [ ] Model router.
- [ ] Prompt versioning.
- [ ] Run state machine.
- [ ] Agent loop.
- [ ] Run event stream.
- [ ] API run endpoints.
- [ ] CLI run commands.

Acceptance:

- [ ] Create agent.
- [ ] Create run.
- [ ] Worker executes run.
- [ ] Final output is persisted.
- [ ] Timeline is persisted.
- [ ] Mock provider deterministic tests pass.
- [ ] OpenAI smoke path is documented.

### Phase 2: Day 8-12 - Tools, Policy, and Approval

Goal:

```text
Let agents call tools safely with policy checks and human approval.
```

Checklist:

- [ ] Tool interface.
- [ ] Tool registry.
- [ ] JSON schema validation.
- [ ] Tool executor.
- [ ] Built-in safe tools.
- [ ] Risk levels.
- [ ] Policy engine.
- [ ] Approval model.
- [ ] Approval API.
- [ ] Approval CLI.
- [ ] Interrupt/resume.
- [ ] Retry/fallback.
- [ ] Audit log.

Acceptance:

- [ ] Safe tool auto-executes.
- [ ] Risky tool pauses run.
- [ ] Approval resumes run.
- [ ] Rejection stops safely.
- [ ] Tool failure retries where safe.
- [ ] Tool calls and decisions are auditable.

### Phase 3: Day 13-18 - RAG and Memory

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
