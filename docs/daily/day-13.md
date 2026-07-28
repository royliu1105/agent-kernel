# Day 13: Phase 2 Retry and Fallback Closure

## Goal

Close Phase 2 by adding conservative retry/fallback behavior to runtime execution.

Day 13 should establish this path:

```text
retryable failure -> retry attempt event -> success or fallback -> final result
non-retryable failure -> fail safely
```

## Scope

Day 13 should cover:

- Phase 2 planning alignment.
- Retry/fallback spec refinement.
- Runtime retry policy model.
- Retry events in run timeline.
- Model provider retry for explicitly retryable provider errors.
- Model fallback through explicit `fallback_models` run input.
- Safe/read-only tool retry for retryable tool execution errors.
- No retry for approval-required or denied tools.
- No retry for invalid tool arguments.
- Unit tests for provider retry/fallback.
- Unit tests for safe tool retry.
- Worker regression tests if behavior changes.
- Documentation and milestone updates.
- Phase 2 closure notes.

Day 13 should not cover:

- Durable external retry queue.
- Backoff timers or delayed scheduling.
- Distributed worker leasing.
- Provider-native function calling.
- Multi-step agent loops.
- Retry API endpoint.
- Web UI.
- Auth/authorization.

## Input Contract

Model fallback is explicit in run input:

```json
{
  "task": "summarize",
  "model": "primary:model",
  "fallback_models": ["backup:model"]
}
```

Retry behavior is controlled by runtime policy. Day 13 defaults are intentionally conservative:

- Retry retryable provider errors once.
- Retry retryable safe/read-only tool errors once.
- Do not retry invalid input.
- Do not retry denied tools.
- Do not retry approval-required tools before approval.
- Do not retry rejected approvals.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-13.md`.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect runtime execution, provider errors, tool errors, worker, and tests.
- [x] Add retry/fallback run event types.
- [x] Add runtime retry policy model.
- [x] Add model provider retry attempts.
- [x] Add explicit model fallback attempts.
- [x] Add safe tool retry attempts.
- [x] Ensure approval-required and denied tools are not retried.
- [x] Add provider retry/fallback tests.
- [x] Add safe tool retry tests.
- [x] Update run lifecycle spec.
- [x] Update tool-calling spec.
- [x] Update security policy spec.
- [x] Update milestones.
- [x] Record Phase 2 closure notes.

## Acceptance

- [x] Retryable provider failure can retry and succeed.
- [x] Retryable provider failure can fall back to another model and succeed.
- [x] Non-retryable provider failure still fails safely.
- [x] Retryable safe tool failure can retry and succeed.
- [x] Invalid tool arguments are not retried.
- [x] Approval-required tools still pause instead of retrying.
- [x] Retry/fallback attempts are visible in run events.
- [x] Phase 2 milestone checklist is closed except explicitly deferred items.

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

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py
```

## Notes

- Retry/fallback is an execution policy, not a new storage table on Day 13.
- Run events are the audit trail for attempts.
- A future durable scheduler can replace in-process retry without changing the public behavior.

## Completion Notes

- Added retry/fallback run event types:
  - `model_call_retrying`
  - `model_fallback_selected`
  - `tool_call_retrying`
- Added `RetryPolicy` to `kernel-runtime`.
- Model calls retry retryable provider errors on the same model.
- Model calls can fall back to explicit `fallback_models` in run input.
- Safe/read-only explicit tools retry retryable tool execution errors.
- Invalid tool arguments are not retried.
- Approval-required tools still pause instead of retrying.
- Denied and side-effecting tools are not automatically retried.
- Retry/fallback attempts are visible in run event timelines.
- Phase 2 milestone checklist is closed.

Verification passed:

- `uv sync`
- `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `docker compose config`
- `pre-commit run --all-files`

Full test result:

- 88 tests passed.
- 1 upstream `StarletteDeprecationWarning` remains from FastAPI/TestClient.

Known caveat:

- Day 13 retry/fallback is in-process and immediate. Durable delayed retries, exponential backoff,
  distributed scheduling, and a public manual retry API are still deferred.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 13：请按照 docs/daily/day-13.md 执行 Phase 2 retry/fallback 收口。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-13.md、docs/specs/run-lifecycle.md、docs/specs/tool-calling.md、docs/specs/security-policy.md 和 docs/milestones.md。
- 只实现 Day 13 scope 内的内容，不提前做 RAG、memory、provider-native function calling、multi-step agent loop、Web UI 或 auth。
- Retry 必须保守，只针对明确 retryable 的 provider/tool 错误。
- Fallback 必须显式来自 run input 的 fallback_models。
- 不要自动重试 denied、approval-required、invalid-arguments 或 rejected approval 路径。
- Retry/fallback 必须写入 run event timeline。
- 完成后运行 Day 13 verification commands。
- 更新 docs/daily/day-13.md 的 checklist。
- 更新 specs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
