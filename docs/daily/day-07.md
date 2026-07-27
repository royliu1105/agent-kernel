# Day 07: Phase 1 Runtime Closure

## Goal

Close Phase 1 by making the core runtime path reproducible, testable, and contributor-friendly.

Day 7 should complete the remaining Phase 1 provider baseline and remove friction from the
end-to-end local path:

```text
create agent -> create run -> queue run -> worker executes -> inspect output and timeline
```

After Day 7, the project should be ready to enter Phase 2 tool calling, policy, and approval work
without carrying obvious Phase 1 gaps.

## Scope

Day 7 should cover:

- Phase 1 planning alignment.
- Replay provider baseline for deterministic regression and eval work.
- Replay provider spec update.
- Replay provider tests without network or API keys.
- Model router support for `replay:*` routes if the provider boundary makes that natural.
- Worker default router update if replay routing is included.
- CLI `run queue <run-id>`.
- CLI `run cancel <run-id>`.
- CLI tests for queue and cancel commands.
- End-to-end integration test covering API create, API queue, worker execute, API inspect, and API
  event timeline.
- Quickstart-style local runtime documentation.
- Daily checklist and Phase 1 milestone updates.

Day 7 should not cover:

- Tool/function calling.
- Policy engine.
- Human approval.
- Retry/fallback semantics.
- Redis-backed queues or distributed worker leases.
- Streaming.
- RAG or memory.
- Web UI.
- Eval runner implementation beyond replay-provider foundation.
- Real OpenAI network tests.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- What should the replay provider replay?
  - Proposed: map model names or request keys to pre-recorded `LLMResponse` objects. Keep it small,
    in-memory, and fixture-friendly.
- Should replay matching inspect the full prompt?
  - Proposed: support simple deterministic lookup first, such as exact model name. Prompt hashing
    can arrive with the eval runner.
- Should replay live in `kernel-providers`?
  - Proposed: yes. It is a provider implementation, not runtime orchestration.
- Should the worker default router include replay?
  - Proposed: yes if the provider is lightweight and has an empty default fixture set. Unknown
    replay models should fail clearly.
- Should CLI queue/cancel duplicate API semantics?
  - Proposed: yes. CLI should call existing API endpoints and print the returned run JSON.
- Should Day 7 add a Web UI path?
  - Resolved: no. Web UI starts later after tools, approval, memory/RAG, observability, and evals
    have enough runtime surface to inspect.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-07.md`.
- [x] Read `docs/specs/providers.md`.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/milestones.md` Phase 1 section.
- [x] Inspect current provider package exports.
- [x] Inspect `ModelRouter` tests.
- [x] Inspect CLI run command tests.
- [x] Inspect API run lifecycle integration tests.
- [x] Design the minimal replay provider contract.
- [x] Implement replay provider baseline.
- [x] Export replay provider from `kernel-providers`.
- [x] Add replay provider unit tests.
- [x] Add or update router tests for `replay:*`.
- [x] Update worker default router if replay provider is registered there.
- [x] Add CLI `run queue <run-id>`.
- [x] Add CLI `run cancel <run-id>`.
- [x] Add CLI tests for queue and cancel.
- [x] Add an end-to-end API + worker integration test.
- [x] Update provider spec with replay semantics.
- [x] Update run lifecycle spec with CLI queue/cancel and E2E path.
- [x] Add or update quickstart/local runtime docs.
- [x] Update `docs/milestones.md` Phase 1 progress.
- [x] Record completion notes in this file.

## Acceptance

- [x] Replay provider exists and implements `LLMProvider`.
- [x] Replay provider tests are deterministic and do not use network.
- [x] Replay provider can be routed through `ModelRouter`.
- [x] CLI can queue a run through `POST /v1/runs/{run_id}/queue`.
- [x] CLI can cancel a run through `POST /v1/runs/{run_id}/cancel`.
- [x] E2E integration test proves API-created queued run can be executed by worker.
- [x] E2E integration test verifies final output.
- [x] E2E integration test verifies timeline events.
- [x] Quickstart docs describe the current real local path without fake commands.
- [x] Phase 1 milestone checklist is updated.
- [x] Tests remain deterministic.

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

Optional manual local runtime path:

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

## Notes

- Day 7 is a closure day, not a scope expansion day.
- Prefer removing friction in the existing path over adding new runtime concepts.
- Replay provider should be boring, explicit, and fixture-friendly.
- Do not build the eval runner yet; replay provider is only the foundation.
- Keep CLI queue/cancel thin wrappers over existing API endpoints.
- Keep the E2E test deterministic by using mock or replay provider only.
- Update docs immediately if the real command shape differs from this plan.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 7：请按照 docs/daily/day-07.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-07.md、docs/specs/providers.md、docs/specs/run-lifecycle.md 和 docs/milestones.md。
- 只实现 Day 7 scope 内的内容，不提前做 tool calling、policy、human approval、retry/fallback、Redis 队列、RAG、memory、eval runner 或 Web UI。
- Replay provider 和 E2E 测试必须 deterministic，不能真实访问网络，也不能要求 API key。
- CLI queue/cancel 必须复用现有 API endpoint 语义。
- 如果 provider routing、run lifecycle 或 CLI 语义变化，更新相关 spec。
- 完成后运行 Day 7 verification commands。
- 更新 docs/daily/day-07.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Added `ReplayLLMProvider` in `kernel-providers`.
- Replay matches routed model names to in-memory `LLMResponse` fixtures.
- Missing replay fixtures raise `LLMProviderError` with `error_type = replay_not_found`.
- Exported replay provider from `kernel-providers`.
- Added `replay:*` model router coverage.
- Registered replay provider in the default worker router.
- Added CLI commands:
  - `uv run agent-kernel run queue <run-id>`
  - `uv run agent-kernel run cancel <run-id>`
- Added deterministic E2E integration test for API-created runs executed by worker.
- Added [Quickstart](../quickstart.md) with the current real local runtime path.
- Updated provider spec, run lifecycle spec, docs index, README, and Phase 1 milestone progress.

Verification passed:

- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `docker compose config`
- `pre-commit run --all-files`

Known caveat:

- Replay is in-memory and model-name matched only. Prompt hashing, fixture file formats, golden
  traces, and eval runner integration are deferred to the eval phase.
