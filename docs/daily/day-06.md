# Day 06: Worker Execution Loop

## Goal

Turn the persisted run lifecycle into a real background execution path.

Day 6 should establish the first production-shaped worker loop:

```text
queued run -> worker picks run -> runtime executes through model router -> result is persisted
```

This is the first point where the project behaves like an actual agent runtime instead of only an
API and storage foundation.

## Scope

Day 6 should cover:

- Phase 1 planning alignment.
- Worker spec and run lifecycle documentation updates.
- Worker application wiring for storage, model routing, and execution service.
- Querying queued runs from the repository.
- Executing queued runs through `RunExecutionService`.
- Persisting successful output and failed execution errors.
- Writing run timeline events during worker execution.
- A one-shot worker mode suitable for local development and CI tests.
- A loop mode suitable for local manual testing.
- Worker CLI flags such as `--once`, `--limit`, and poll interval if needed.
- Tests for queued-run execution, provider failure handling, and terminal-run safety.
- Documentation for local worker usage.
- Updating Phase 1 milestone progress if acceptance criteria become true.

Day 6 should not cover:

- Redis-backed durable queues.
- Distributed worker leasing or heartbeats.
- Concurrency across multiple worker processes.
- Streaming model responses.
- Tool/function calling.
- Human approval or interrupt/resume.
- Retry/fallback policy.
- RAG, memory, or Web UI.
- Real OpenAI network smoke tests.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Where should worker orchestration logic live?
  - Proposed: keep reusable execution orchestration in `kernel-runtime`; keep process/config wiring
    in `apps/worker`.
- Should Day 6 use Redis as a queue?
  - Proposed: no. Use the persisted `runs.status = queued` table as the MVP queue. Redis can be
    added later for scheduling, pub/sub, or rate limiting once the durable run model is stable.
- Should the worker run forever by default?
  - Proposed: default to a safe one-shot or explicit mode. A local loop mode can exist, but tests
    should use deterministic one-shot execution.
- What provider should the worker use by default?
  - Proposed: register `MockLLMProvider` by default so the worker can run locally without API keys.
    OpenAI routing can be available only when an `openai:*` model is used and `OPENAI_API_KEY` is
    configured.
- What counts as the Day 6 "agent loop"?
  - Proposed: a minimal single-step loop: build an LLM request from the run input, route to provider,
    persist output, and emit events. Multi-step planning/tool loops should wait for Phase 2.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-06.md`.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/specs/providers.md`.
- [x] Read `docs/milestones.md` Phase 1 section.
- [x] Inspect current worker app entrypoint.
- [x] Inspect runtime execution service and repository APIs.
- [x] Decide worker orchestration boundary between `kernel-runtime` and `apps/worker`.
- [x] Add or update worker runtime orchestration code.
- [x] Wire worker app to database session creation.
- [x] Wire worker app to default model router.
- [x] Add one-shot worker execution mode.
- [x] Add local loop worker mode if it remains small.
- [x] Add worker CLI flags.
- [x] Add tests for executing queued runs successfully.
- [x] Add tests for provider failure handling.
- [x] Add tests proving terminal runs are not re-executed.
- [x] Update run lifecycle spec with worker behavior.
- [x] Update provider spec if worker routing behavior changes.
- [x] Update local development docs or README with worker usage.
- [x] Update `docs/milestones.md` Phase 1 progress.
- [x] Record completion notes in this file.

## Acceptance

- [x] A queued run can be executed by the worker.
- [x] Worker execution persists final output.
- [x] Worker execution persists failure errors.
- [x] Worker execution emits timeline events.
- [x] Worker execution uses `ModelRouter`.
- [x] Worker defaults to deterministic mock execution for local development and tests.
- [x] OpenAI remains opt-in and does not run in normal tests.
- [x] Terminal runs are not accidentally re-executed.
- [x] Worker has a clear local command.
- [x] Tests remain deterministic.
- [x] Phase 1 milestone checklist is updated.

## Verification

Run the available checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
docker compose config
pre-commit run --all-files
```

Optional manual worker path after implementation:

```bash
uv run agent-kernel-worker --once --limit 10
```

If the API and database are running locally, also verify the end-to-end path manually:

```bash
docker compose up -d postgres redis
uv run alembic upgrade head
uv run agent-kernel-api
uv run agent-kernel agent create --name "Local Test Agent"
uv run agent-kernel run create <agent-id> --input '{"task":"hello worker","model":"mock:echo"}'
curl -X POST http://127.0.0.1:8000/v1/runs/<run-id>/queue
uv run agent-kernel-worker --once
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

## Notes

- Keep the Day 6 worker intentionally boring and reliable.
- Prefer deterministic behavior over a sophisticated scheduler.
- Treat Postgres as the durable source of truth for MVP execution.
- Do not introduce Redis queue semantics until worker state transitions and recovery behavior are
  well tested.
- Do not make real OpenAI calls in automated tests.
- Avoid over-generalizing the worker before tool calling and approval semantics exist.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 6：请按照 docs/daily/day-06.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-06.md、docs/specs/run-lifecycle.md、docs/specs/providers.md 和 docs/milestones.md。
- 只实现 Day 6 scope 内的内容，不提前做 Redis 队列、分布式 worker、tool calling、human approval、retry/fallback、RAG、memory 或 Web UI。
- Worker 默认必须可以使用 mock provider 本地执行，不要求真实 OpenAI API key。
- 自动化测试不能真实访问网络，也不能要求 API key。
- 如果 worker execution、run lifecycle 或 provider routing 语义变化，更新相关 spec。
- 完成后运行 Day 6 verification commands。
- 更新 docs/daily/day-06.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Added `QueuedRunWorker`, `WorkerBatchResult`, and `WorkerRunResult` in `kernel-runtime`.
- Worker polling uses persisted queued runs from `RunRepository.list_queued`.
- Each picked run executes in its own database session to isolate batch failures.
- Worker app now supports:
  - `uv run agent-kernel-worker`
  - `uv run agent-kernel-worker --once --limit 10`
  - `uv run agent-kernel-worker --loop --limit 10 --poll-interval 5`
- Worker default router registers `mock` and `openai`.
- Mock execution remains deterministic and requires no network or API key.
- OpenAI remains opt-in through `openai:*` model references and `OPENAI_API_KEY`.
- Runtime execution now marks expected setup errors, such as unknown model routes, as failed runs
  instead of leaving them stuck in `running`.
- Added worker tests for success, provider failure, terminal-run safety, route-error failure, and
  invalid limits.
- Updated run lifecycle, provider, development environment, README, and milestone docs.

Verification passed:

- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `docker compose config`
- `pre-commit run --all-files`
- `uv run alembic upgrade head`
- `uv run agent-kernel-worker --once --limit 10`

Known caveat:

- Worker execution is single-process and non-leased. Distributed worker coordination, heartbeats,
  Redis-backed scheduling, and crash recovery leases remain deferred.
