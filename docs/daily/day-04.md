# Day 04: LLM Provider Interface and Deterministic Execution

## Goal

Turn a queued run into the first deterministic executed run without calling a real LLM.

Day 4 should establish the service path for:

```text
queued run -> runtime execution service -> mock LLM provider -> persisted final output -> succeeded
```

This is not the production worker loop yet. The focus is model provider abstraction,
deterministic execution, and persisted output semantics.

## Scope

Day 4 should cover:

- Phase 1 planning alignment.
- Provider interface spec refinement.
- Core LLM request/response/message/usage/error models.
- `LLMProvider` protocol or abstract base.
- Deterministic `MockLLMProvider`.
- Minimal runtime execution service for one queued run.
- Run transition from `queued` to `running` to `succeeded`.
- Failure path from provider error to `failed`.
- Persisted final run output.
- Timeline events for `run_started`, `run_completed`, and `run_failed`.
- Tests for provider contract, mock provider, execution success, and execution failure.

Day 4 should not cover:

- OpenAI provider.
- Model router.
- Prompt versioning.
- Streaming.
- Tool calling.
- Multi-step planning.
- Worker process polling loop.
- Redis-backed queue.
- Human approval.
- Web UI changes.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Where should provider domain types live?
  - Resolved: provider-specific interfaces and DTOs live in `kernel-providers`; runtime imports
    only the stable provider interface.
- Should provider methods be sync or async?
  - Resolved: async interface, because real provider calls are network I/O and future streaming
    or concurrent execution should not require a breaking interface change.
- Should Day 4 add OpenAI SDK dependencies?
  - Resolved: no. Day 4 remains deterministic and offline.
- What should the mock provider return?
  - Resolved: deterministic text based on input messages, plus stable token usage metadata.
- Where should final output be persisted?
  - Resolved: `runs.output` as JSON, with an initial shape including text, provider, model,
    and usage.
- Should execution service own state transitions?
  - Resolved: yes. Execution calls `RunStateMachine` and repository transition methods.
- Should Day 4 execute only queued runs?
  - Resolved: yes. Running a `created`, `succeeded`, `failed`, or `canceled` run fails
    clearly.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/milestones.md` Phase 1 section.
- [x] Add or update provider interface spec if needed.
- [x] Add provider request/response/message/usage/error models in `kernel-providers`.
- [x] Add `LLMProvider` interface.
- [x] Add deterministic `MockLLMProvider`.
- [x] Add unit tests for provider models and mock provider behavior.
- [x] Add runtime execution service for a single queued run.
- [x] Add repository method to update run output and usage totals.
- [x] Add repository method to mark run failure details if needed.
- [x] Wire execution service through `RunStateMachine`.
- [x] Add execution success tests.
- [x] Add execution failure tests.
- [x] Update `docs/specs/run-lifecycle.md` with Day 4 execution semantics.
- [x] Update `docs/milestones.md` Phase 1 progress.

## Acceptance

- [x] `LLMProvider` interface exists and is typed.
- [x] `MockLLMProvider` returns deterministic output.
- [x] A queued run can be executed by the runtime service.
- [x] Execution moves run through `queued -> running -> succeeded`.
- [x] Successful execution persists final output.
- [x] Successful execution appends `run_started` and `run_completed` events.
- [x] Provider failure moves run to `failed`.
- [x] Provider failure persists error type/message.
- [x] Provider failure appends `run_failed` event.
- [x] Tests are deterministic and require no network/API key.
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

If a local execution smoke test is useful, keep it API-free for Day 4:

```bash
uv run pytest tests/unit/test_mock_provider.py tests/unit/test_runtime_execution.py
```

## Notes

- Keep the provider interface minimal but production-shaped.
- Do not add real provider dependencies until the mock contract is stable.
- Keep mock behavior deterministic so it can become the foundation for evals and regression tests.
- Keep execution service single-run and explicit; the polling worker loop belongs to a later day.
- Use persisted run state and append-only events as the source of truth.

## Completion Notes

- Implemented typed provider DTOs: `LLMMessage`, `LLMRequest`, `LLMResponse`, and `LLMUsage`.
- Added async `LLMProvider` protocol and typed `LLMProviderError`.
- Added deterministic, offline `MockLLMProvider`.
- Added single-run `RunExecutionService`.
- Added repository methods for successful completion and provider failure persistence.
- Added provider spec in `docs/specs/providers.md`.
- Updated run lifecycle spec with Day 4 execution semantics.
- Added deterministic provider, runtime execution, and storage tests.
- Verification passed:
  - `uv sync`
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `docker compose ps`
  - `docker compose config`
  - `pre-commit run --all-files`

Known caveat:

- Execution is still API-free and worker-free. Day 4 proves the runtime path; Day 5/6 should expose
  it through model routing and worker execution.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 4：请按照 docs/daily/day-04.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-04.md、docs/specs/run-lifecycle.md 和 docs/milestones.md。
- 只实现 Day 4 scope 内的内容，不提前做 OpenAI provider、model router、worker loop、tool calling 或 Web UI。
- 如果 provider 或 execution 语义变化，更新相关 spec。
- 完成后运行 Day 4 verification commands。
- 更新 docs/daily/day-04.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
