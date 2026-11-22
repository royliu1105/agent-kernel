# Day 03: Run State Machine and CLI Operations

## Goal

Turn the persisted Day 2 run lifecycle into a controlled execution state model.

Day 3 should establish the service path for:

```text
create agent -> create run -> queue run -> inspect status -> inspect timeline
```

This is still not the full agent execution loop. The focus is legal state transitions,
append-only timeline events, and developer-facing CLI ergonomics.

## Scope

Day 3 should cover:

- Phase 1 planning alignment.
- Run lifecycle spec refinement for transition rules.
- A runtime/service-level run state machine.
- Explicit legal transition table.
- Error type for invalid run transitions.
- Repository methods for updating run status and appending run events.
- Repository method for listing queued runs.
- API endpoints for queueing and canceling runs.
- CLI commands for creating agents, creating runs, inspecting runs, and listing events.
- Tests for valid transitions, invalid transitions, API transitions, and CLI smoke behavior.

Day 3 should not cover:

- OpenAI provider.
- Mock provider.
- Model router.
- Prompt versioning.
- Worker execution loop.
- Tool calling.
- Approval/resume.
- Retry semantics beyond documenting later behavior.
- Redis-backed queue.
- Web UI changes.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Should the state machine live in `kernel-runtime` or `kernel-storage`?
  - Resolved: `kernel-runtime`, because transition semantics are runtime behavior, while storage
    should stay persistence-focused.
- Should repository methods enforce legal transitions?
  - Resolved: no. Repositories persist state; the runtime state machine enforces legality.
- What events should Day 3 emit?
  - Resolved: `run_queued`, `run_started`, `run_completed`, `run_failed`, and `run_canceled`
    when the corresponding transition occurs.
- Should queueing immediately use Redis?
  - Resolved: no. Day 3 marks a run as `queued` in Postgres; Redis/task queue integration waits
    until worker execution needs it.
- Should cancel be allowed from every state?
  - Resolved: allow cancel from `created`, `queued`, `running`, `waiting_approval`, and
    `resuming`; reject cancel from terminal states.
- Should CLI talk to the API or directly to storage?
  - Resolved: CLI should talk to the API by default. Direct storage access can be a later
    admin/dev mode if needed.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/milestones.md` Phase 1 section.
- [x] Refine `docs/specs/run-lifecycle.md` with Day 3 transition rules.
- [x] Add runtime error types for invalid transitions.
- [x] Add `RunStateMachine` or equivalent transition service in `kernel-runtime`.
- [x] Add unit tests for valid run transitions.
- [x] Add unit tests for invalid run transitions.
- [x] Add repository method to update run status fields.
- [x] Add repository method to append run events with monotonic sequence.
- [x] Add repository method to list queued runs.
- [x] Add API schema for run transition responses if needed.
- [x] Add `POST /v1/runs/{run_id}/queue`.
- [x] Add `POST /v1/runs/{run_id}/cancel`.
- [x] Add API integration tests for queue/cancel flows.
- [x] Add CLI configuration for API base URL.
- [x] Add `agent-kernel agent create`.
- [x] Add `agent-kernel run create`.
- [x] Add `agent-kernel run inspect`.
- [x] Add `agent-kernel run events`.
- [x] Add CLI tests or smoke tests.
- [x] Update `docs/milestones.md` Phase 1 progress.

## Acceptance

- [x] A created run can be queued through the API.
- [x] Queueing a run appends a `run_queued` event.
- [x] A queued or running run can be canceled through the API.
- [x] Canceling a run appends a `run_canceled` event.
- [x] Invalid transitions are rejected with a clear error.
- [x] Repository tests cover status update and event append behavior.
- [x] Runtime tests cover legal and illegal state transitions.
- [x] API tests cover queue and cancel flows.
- [x] CLI can create an agent.
- [x] CLI can create a run.
- [x] CLI can inspect a run.
- [x] CLI can list run events.
- [x] Phase 1 checklist is updated for completed items.

## Verification

Run the available checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
docker compose ps
docker compose config
pre-commit run --all-files
```

If API smoke testing is useful:

```bash
DATABASE_URL=postgresql+psycopg://agent_kernel:agent_kernel@localhost:5432/agent_kernel \
  uv run uvicorn agent_kernel_api.main:app --reload

curl http://127.0.0.1:8000/healthz
```

Expected CLI smoke shape:

```bash
agent-kernel agent create --name research-agent --description "Research assistant"
agent-kernel run create <agent-id> --input '{"task":"summarize notes"}'
agent-kernel run inspect <run-id>
agent-kernel run events <run-id>
```

## Notes

- Keep Day 3 focused on transition semantics and developer ergonomics.
- Do not implement the worker execution loop until state transitions are centralized.
- Do not introduce Redis queueing yet; persisted `queued` status is enough for Day 3.
- Prefer runtime service methods over endpoint-local transition logic.
- Keep CLI commands thin and API-backed so behavior stays consistent across interfaces.

## Completion Notes

- Implemented `RunStateMachine` in `kernel-runtime`.
- Added invalid transition errors and transition event mapping.
- Added repository methods for status updates, append-only events, atomic transitions, and queued
  run listing.
- Added `POST /v1/runs/{run_id}/queue`.
- Added `POST /v1/runs/{run_id}/cancel`.
- Added API-backed CLI commands for agent creation, run creation, run inspection, and run events.
- Added runtime, repository, API, and CLI tests.
- Verification passed:
  - `uv sync`
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `docker compose ps`
  - `docker compose config`
  - `pre-commit run --all-files`

Known caveat:

- CLI queue/cancel commands are intentionally deferred. Day 3 only required CLI create/inspect/event
  operations; cancellation is currently available through the API.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 3：请按照 docs/daily/day-03.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-03.md、docs/specs/run-lifecycle.md 和 docs/milestones.md。
- 只实现 Day 3 scope 内的内容，不提前做 LLM provider、worker loop、tool calling 或 Web UI。
- 如果状态转换语义变化，更新 docs/specs/run-lifecycle.md。
- 完成后运行 Day 3 verification commands。
- 更新 docs/daily/day-03.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
