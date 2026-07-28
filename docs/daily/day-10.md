# Day 10: Persisted Tool Calls and Audit Timeline

## Goal

Persist tool calls and policy decisions so Phase 2 can become inspectable and auditable.

Day 10 should establish this path:

```text
tool requested -> persisted ToolCall -> policy decision recorded -> result/error recorded
```

This prepares the database and timeline for approval workflows without implementing approval itself.

## Scope

Day 10 should cover:

- Phase 2 planning alignment.
- Tool calling spec refinement for persistence.
- Security policy spec refinement for audit baseline.
- `tool_calls` storage model.
- Alembic migration for `tool_calls`.
- Tool call repository.
- Persisting requested tool calls.
- Listing tool calls for a run.
- Recording policy checked / denied / waiting approval state.
- Recording tool success.
- Recording tool failure.
- Run event timeline entries for tool call and policy decisions.
- Tests for tool call persistence.
- Tests for status updates.
- Tests for run event audit timeline.
- Milestone updates.

Day 10 should not cover:

- Approval persistence.
- Approval API or CLI.
- Run `waiting_approval` integration.
- Interrupt/resume.
- Agent run loop integration.
- Provider-native tool/function calling.
- Retry/fallback.
- External audit sink.
- Web UI.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Should `ToolCall` use the existing domain model?
  - Proposed: yes. Extend storage around the existing `kernel_core.ToolCall`.
- Should policy package depend on storage?
  - Proposed: no. Storage should persist generic policy decision strings and payloads.
- Should Day 10 add a separate `audit_events` table?
  - Proposed: defer. Use persisted `run_events` as the audit timeline baseline first.
- Which run events are needed?
  - Proposed: `tool_call_requested`, `policy_evaluated`, `tool_call_completed`, and
    `tool_call_failed`.
- Should Day 10 expose tool calls through API?
  - Proposed: no. Repository and timeline first; API can follow once approval model is introduced.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-10.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/specs/approval-resume.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect current storage models and migration.
- [x] Inspect existing `ToolCall` domain model.
- [x] Add tool call run event types.
- [x] Add `ToolCallRecord`.
- [x] Add Alembic migration for `tool_calls`.
- [x] Add `ToolCallRepository`.
- [x] Add mapping between storage records and domain `ToolCall`.
- [x] Add requested tool call persistence.
- [x] Add policy decision recording.
- [x] Add success recording.
- [x] Add failure recording.
- [x] Add list-by-run query.
- [x] Add repository tests.
- [x] Update `docs/specs/tool-calling.md`.
- [x] Update `docs/specs/security-policy.md`.
- [x] Update `docs/milestones.md` Phase 2 progress.
- [x] Record completion notes in this file.

## Acceptance

- [x] `tool_calls` table model exists.
- [x] Migration exists.
- [x] Tool calls can be persisted as requested.
- [x] Tool calls can be listed by run.
- [x] Policy checked state can be recorded.
- [x] Denied state can be recorded.
- [x] Waiting approval state can be recorded.
- [x] Successful result can be recorded.
- [x] Failure error can be recorded.
- [x] Run events capture audit timeline entries.
- [x] Tests remain deterministic.
- [x] Phase 2 milestone checklist is updated.

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
uv run pytest tests/unit/test_tool_call_repository.py
```

## Notes

- Day 10 is persistence and timeline only.
- Do not create approval records yet.
- Do not move runs to `waiting_approval` yet.
- Do not integrate with the agent execution loop yet.
- Use run events as the first audit trail.
- Keep storage independent from policy package internals.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 10：请按照 docs/daily/day-10.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-10.md、docs/specs/tool-calling.md、docs/specs/security-policy.md、docs/specs/approval-resume.md 和 docs/milestones.md。
- 只实现 Day 10 scope 内的内容，不提前做 approval persistence、approval API/CLI、run waiting_approval integration、interrupt/resume、agent run loop integration、retry/fallback、RAG、memory 或 Web UI。
- 使用 run events 作为 Day 10 audit timeline baseline。
- 如果 tool call persistence 或 audit event 语义变化，更新相关 spec。
- 完成后运行 Day 10 verification commands。
- 更新 docs/daily/day-10.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Added tool call run event types:
  - `policy_evaluated`
  - `tool_call_completed`
  - `tool_call_failed`
- Added `ToolCallRecord`.
- Added Alembic migration `0002_create_tool_calls`.
- Added `ToolCallRepository`.
- Tool calls can now be persisted as requested.
- Tool calls can be listed by run.
- Policy decisions can update tool call state.
- Denied and waiting-approval states can be recorded.
- Tool call success and failure can be recorded.
- Tool call and policy events are appended to the run timeline.
- Added `tests/unit/test_tool_call_repository.py`.
- Updated tool calling and security policy specs.
- Updated Phase 2 milestones with audit baseline progress.

Verification passed:

- `uv run pytest tests/unit/test_tool_call_repository.py tests/unit/test_storage_repositories.py`
- `uv run ruff check .`
- `uv run mypy .`

Known caveat:

- Day 10 uses run events as the audit timeline baseline. Dedicated audit tables, approval records,
  approval decisions, API exposure, and run `waiting_approval` integration remain deferred.
