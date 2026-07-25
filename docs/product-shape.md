# Product Shape and Capabilities

## Product Form

Agent Kernel is not a simple chat application. It is a self-hosted production-grade AI Agent runtime and developer platform.

The intended product experience is an Agent Workbench. Chat is one possible task input mode, not the whole product. See [User Experience](user-experience.md) for the UX baseline.

The project should ship as:

```text
A GitHub open-source monorepo
A Python Agent runtime
A FastAPI API server
A background worker
A Typer CLI
A Next.js Web console
A Docker Compose deployment
Documentation, examples, and eval datasets
```

In plain terms:

```text
Agent Kernel = Agent operating-system kernel + control plane + CLI + API
```

## How Users Run It

A user should be able to clone the repository and start the local stack:

```bash
docker compose up
```

The local stack should include:

```text
API server
Worker
Web UI
PostgreSQL + pgvector
Redis
```

Users should be able to operate the system through:

```text
CLI
REST API
Web UI
```

## Core Product Capabilities

### Agent Creation and Configuration

Users can create and configure agents with:

- Name.
- Description.
- System prompt.
- Prompt version.
- Default model policy.
- Available tools.
- Tool permissions.
- Memory policy.
- RAG knowledge base.
- Approval rules.

Example:

```bash
agent-kernel agent create --name research-agent --prompt prompts/research.md
```

### Agent Runs

Users can start an agent run:

```bash
agent-kernel run create <agent-id> --input "Summarize these architecture docs"
```

The system should:

- Create a run.
- Persist run state.
- Enqueue execution.
- Let a worker execute it.
- Persist every step.
- Return a final result.

Run lifecycle:

```text
created -> queued -> running -> waiting_approval -> resumed -> succeeded/failed/canceled
```

### LLM Provider Abstraction

MVP providers:

- OpenAI provider.
- Mock provider.
- Replay provider.

Provider capabilities:

- Model calls.
- Tool/function calling.
- Token usage.
- Cost tracking.
- Fallback.
- Deterministic tests.
- Replay regression tests.

Later providers:

- Anthropic.
- Gemini.
- Ollama.
- vLLM.
- Azure OpenAI.

### Tool Calling

Agents can call registered tools.

Every tool should define:

- Name.
- Description.
- JSON schema.
- Risk level.
- Timeout.
- Permission policy.
- Input validation.
- Output validation.

MVP built-in tools may include:

- `calculator`
- `echo`
- `http_fetch`
- `kb_search`

The default install must not expose an arbitrary shell tool.

### Permissions, Approval, and Resume

Risky tool calls should not execute automatically.

The system should:

- Create an approval request.
- Pause the run.
- Wait for a human decision.
- Resume on approval.
- Stop safely on rejection.

CLI:

```bash
agent-kernel approval list
agent-kernel approval approve <approval-id>
agent-kernel approval reject <approval-id> --reason "Not allowed"
```

The Web UI should provide an approval inbox.

### RAG and Knowledge Base

Users can upload and ingest documents:

```bash
agent-kernel doc upload ./docs/*.md
agent-kernel doc ingest <document-id>
```

The system should:

- Store original documents.
- Parse text.
- Chunk documents.
- Generate embeddings.
- Store vectors in pgvector.
- Retrieve relevant chunks.
- Build citations.
- Let agents call `kb_search`.

Agent answers should support source citations.

### Memory

MVP memory types:

- Short-term memory from current run context.
- Task context for the current run.
- User preferences.
- Long-term memory items.

Memory should be:

- Writable.
- Retrievable.
- Scoped.
- Deletable.
- Source-aware.
- Confidence-aware.

### Workflow and State Machine

MVP uses a database-backed run state machine.

Required capabilities:

- Persisted steps.
- Retry on failure.
- Fallback on model/provider failure.
- Pause on approval.
- Resume after approval.
- Recover after worker crash.

Later:

- Temporal adapter.
- Workflow graph.
- Multi-agent handoff.

### Observability

MVP observability stack:

```text
OpenTelemetry + structlog + Postgres run/step/cost summary
```

Users should be able to inspect:

- Run trace ID.
- Step latency.
- Model call token usage.
- Model call cost.
- Tool call status.
- Tool call latency.
- Retrieval latency.
- Approval wait time.
- Errors.
- Retries.
- Fallbacks.

### Evals and Regression Testing

Users can define and run evals:

```bash
agent-kernel eval run ./evals/research.yaml --agent <agent-id>
agent-kernel eval report <eval-run-id>
```

MVP eval capabilities:

- Deterministic mock eval.
- Expected tool calls.
- Forbidden behavior.
- Required citations.
- Maximum step count.
- Maximum cost.
- Regression report.
- Cheap CI eval.

### Prompt and Version Management

Every run should bind to a prompt version.

This supports:

- Reproducibility.
- Eval comparison.
- Regression diagnosis.
- Prompt behavior tracking.

### API Server

The FastAPI server exposes:

- Agents.
- Runs.
- Approvals.
- Tools.
- Documents.
- Retrieval.
- Memory.
- Evals.

The API creates state and enqueues work. It does not execute long-running agent loops directly.

### CLI

The CLI is the developer-first interface.

It should support:

- Project initialization.
- Local development.
- Agent management.
- Run creation and inspection.
- Approval decisions.
- Document upload and ingestion.
- Knowledge-base queries.
- Eval execution and reporting.

### Web UI

The Web UI is an operations console, not a chat demo.

MVP pages:

- Dashboard.
- Agents.
- Run timeline.
- Tool call detail.
- Approval inbox.
- Knowledge base.
- Eval reports.
- Settings.

The UI should help users answer:

- What did the agent do?
- Why did it do that?
- Which model did it call?
- Which tools did it call?
- What did it retrieve?
- What failed?
- What needs approval?
- How much did it cost?
- Did eval behavior regress?

## Product Value

Agent Kernel's value is not that it can chat.

Its value is that agent execution becomes:

- Controllable.
- Recoverable.
- Auditable.
- Observable.
- Evaluable.
- Extensible.
- Deployable.

## v0.1 Success Criteria

v0.1 succeeds when a new user can:

- Start the stack.
- Create an agent.
- Run the agent.
- See a persisted run timeline.
- Let the agent call tools.
- Pause and resume through approval.
- Upload and retrieve documents.
- Run a basic eval.
- Inspect cost, latency, errors, and trace IDs.
- Understand the architecture from docs.
