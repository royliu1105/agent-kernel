# Phase 1 Summary: Core Runtime

## Status

Phase 1 is complete.

The project now has the first real Agent Kernel runtime path:

```text
create agent
-> create run
-> queue run
-> worker picks queued run
-> model router selects provider
-> provider returns response
-> runtime persists output or failure
-> timeline events are persisted
-> CLI/API inspect result
```

This means Agent Kernel is no longer only a project skeleton. It has a testable, inspectable,
recoverable foundation for agent execution.

## Phase Goal

Phase 1 goal:

```text
Create the first real agent run lifecycle.
```

The lifecycle had to be:

- Persisted.
- State-machine driven.
- Provider-agnostic.
- Worker-executable.
- Inspectable through API and CLI.
- Covered by deterministic tests.
- Documented well enough for future contributors.

## Daily Delivery

### Day 2: Run Lifecycle and Storage Foundation

Delivered:

- `Agent`, `Run`, `RunStep`, and `RunEvent` storage models.
- SQLite/Postgres-compatible ID and JSON storage conventions.
- Alembic migration `0001_create_execution_tables`.
- Repository layer for agents, runs, and run events.
- API endpoints for creating and inspecting agents/runs.
- Persisted run event timeline.

Outcome:

```text
The system could create and inspect persisted agent runs.
```

### Day 3: Run State Machine and CLI Operations

Delivered:

- `RunStateMachine`.
- Validated run transitions.
- Queue and cancel transitions.
- Transition event persistence.
- CLI commands for creating agents/runs and inspecting runs/events.

Outcome:

```text
Run lifecycle state became explicit and protected by runtime rules.
```

### Day 4: LLM Provider Interface and Deterministic Execution

Delivered:

- `LLMProvider` interface.
- Provider request/response/usage/message models.
- `MockLLMProvider`.
- `RunExecutionService`.
- Single-step deterministic execution path.
- Success and provider-failure persistence.

Outcome:

```text
A queued run could be executed through a provider and persisted as succeeded or failed.
```

### Day 5: Model Router and OpenAI Provider Baseline

Delivered:

- `ModelRouter`.
- Explicit provider-prefixed model references.
- `mock:<model>` route.
- `openai:<model>` route.
- OpenAI Responses API adapter baseline.
- `OPENAI_API_KEY` configuration path.
- Prompt versioning baseline.

Outcome:

```text
Runtime execution became provider-routed and ready for real provider integration.
```

### Day 6: Worker Execution Loop

Delivered:

- `QueuedRunWorker`.
- Worker batch result types.
- Worker CLI modes:
  - `agent-kernel-worker`
  - `agent-kernel-worker --once --limit 10`
  - `agent-kernel-worker --loop --limit 10 --poll-interval 5`
- Persisted queued-run polling.
- Worker execution through `RunExecutionService` and `ModelRouter`.
- Failure isolation per run.
- Terminal-run safety tests.
- Execution setup errors are persisted as failed runs.

Outcome:

```text
Queued runs could be executed by a background worker.
```

### Day 7: Phase 1 Runtime Closure

Delivered:

- `ReplayLLMProvider`.
- `replay:<case>` route.
- CLI commands:
  - `agent-kernel run queue <run-id>`
  - `agent-kernel run cancel <run-id>`
- API + worker E2E integration test.
- Quickstart documentation.
- Phase 1 milestone closure.

Outcome:

```text
The end-to-end runtime path became reproducible from API, CLI, worker, and tests.
```

## Current Capabilities

### API

Implemented:

```http
GET  /healthz
POST /v1/agents
GET  /v1/agents/{agent_id}
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/queue
POST /v1/runs/{run_id}/cancel
```

### CLI

Implemented:

```bash
agent-kernel --version
agent-kernel dev
agent-kernel agent create --name "..."
agent-kernel run create <agent-id> --input '{"task":"...","model":"mock:echo"}'
agent-kernel run queue <run-id>
agent-kernel run cancel <run-id>
agent-kernel run inspect <run-id>
agent-kernel run events <run-id>
```

### Worker

Implemented:

```bash
agent-kernel-worker
agent-kernel-worker --once --limit 10
agent-kernel-worker --loop --limit 10 --poll-interval 5
```

Worker behavior:

- Uses persisted `queued` runs as the MVP queue.
- Executes runs one at a time.
- Opens a separate database session per picked run.
- Persists successful output.
- Persists expected execution failures.
- Emits run lifecycle events.

### Providers

Implemented:

```text
mock:<model>   -> MockLLMProvider
openai:<model> -> OpenAIProvider
replay:<case>  -> ReplayLLMProvider
```

Provider roles:

- `mock`: deterministic local development and tests.
- `openai`: real provider baseline using OpenAI Responses API shape.
- `replay`: deterministic regression/eval fixture foundation.

### Runtime

Implemented:

- Run lifecycle state machine.
- Single-step agent execution loop.
- Provider routing.
- Prompt versioning baseline.
- Run output persistence.
- Run error persistence.
- Token and estimated cost persistence.
- Run event timeline persistence.

## Persistence Model

Phase 1 persists:

- Agents.
- Runs.
- Run steps schema baseline.
- Run events.
- Run input.
- Run output.
- Error type/message.
- Token totals.
- Estimated cost total.
- Started/ended timestamps.

The first migration is:

```text
0001_create_execution_tables
```

The default local database is SQLite under `.agent-kernel/`. Production-like development can use
Postgres through `DATABASE_URL`.

## Quality Status

Latest Phase 1 verification:

```text
uv sync
uv run pytest              -> 42 passed, 1 known warning
uv run ruff check .        -> passed
uv run mypy .              -> passed
docker compose config      -> passed
pre-commit run --all-files -> passed
```

Known warning:

- FastAPI/Starlette `TestClient` emits a deprecation warning about `httpx`. Tests pass; revisit when
  the dependency ecosystem settles.

## Test Coverage

Phase 1 includes:

- Domain model tests.
- Storage repository tests.
- API run lifecycle integration tests.
- CLI command tests.
- Run state machine tests.
- Mock provider tests.
- OpenAI provider adapter tests with mocked transport.
- Replay provider tests.
- Model router tests.
- Runtime execution tests.
- Worker execution tests.
- API + worker E2E integration test.

Important test guarantee:

```text
Normal tests do not require network access or real API keys.
```

## Deliberate Non-Goals

Phase 1 intentionally did not implement:

- Tool/function calling.
- Tool registry.
- Policy engine.
- Human approval.
- Interrupt/resume.
- Retry/fallback.
- Redis-backed queues.
- Distributed worker leasing.
- Worker heartbeats.
- Streaming model responses.
- RAG.
- Memory.
- Web UI.
- Eval runner.
- Production observability backend.

These were deferred because Phase 1 needed to stabilize the execution lifecycle first.

## Key Tradeoffs

### Persisted Runs As MVP Queue

The worker uses `runs.status = queued` as the MVP queue.

Why:

- Simple.
- Durable.
- Easy to test.
- Good enough before distributed execution semantics exist.

Deferred:

- Redis scheduling.
- Leasing.
- Heartbeats.
- Multi-worker concurrency.
- Crash recovery leases.

### Single-Step Agent Loop

The initial agent loop performs one provider call.

Why:

- It validates the lifecycle without prematurely designing tools and planning.
- Tool loops need policy and approval semantics, which belong in Phase 2.

Deferred:

- Multi-step planning.
- Tool call loops.
- Approval pauses.
- Resume from intermediate steps.

### In-Memory Replay Provider

Replay currently matches by routed model name.

Why:

- Keeps regression fixture behavior deterministic and small.
- Avoids designing eval dataset formats too early.

Deferred:

- Prompt hashing.
- Fixture files.
- Golden traces.
- Eval runner integration.

## How To Run The Current Path

Use the quickstart:

```text
docs/quickstart.md
```

Minimal command shape:

```bash
uv run alembic upgrade head
uv run agent-kernel-api
uv run agent-kernel agent create --name "Local Test Agent"
uv run agent-kernel run create <agent-id> --input '{"task":"hello runtime","model":"mock:echo"}'
uv run agent-kernel run queue <run-id>
uv run agent-kernel-worker --once --limit 10
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

Expected timeline:

```text
run_created
run_queued
run_started
run_completed
```

## Phase 2 Entry Criteria

Phase 2 can start because:

- Runs can be created and persisted.
- Runs can be queued and canceled.
- Runs can be executed by a worker.
- Provider calls are abstracted and routed.
- Results and failures are persisted.
- Timeline events are inspectable.
- CLI and API can drive the path.
- Deterministic tests prove the full path.

## Next Phase

Phase 2 should focus on:

- Tool interface.
- Tool registry.
- JSON schema validation.
- Tool executor.
- Risk levels.
- Policy engine.
- Approval model.
- Approval API and CLI.
- Interrupt/resume.
- Retry/fallback.
- Audit log.

The next major project shift is:

```text
from "agent can call a model"
to "agent can safely call tools"
```
