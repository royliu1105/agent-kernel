# Day 11: Approval Records, API, and CLI

## Goal

Add the first human-in-the-loop approval surface.

Day 11 should establish this path:

```text
approval requested -> operator lists approval -> approve or reject -> decision is audited
```

This makes approval decisions real and inspectable. Run pause/resume integration is deferred to
Day 12.

## Scope

Day 11 should cover:

- Phase 2 planning alignment.
- Approval spec refinement.
- `approvals` storage model.
- Alembic migration for `approvals`.
- Approval repository.
- Creating requested approvals for persisted tool calls.
- Listing approvals.
- Getting one approval.
- Approving an approval.
- Rejecting an approval with a reason/note.
- Preventing duplicate decisions.
- Recording decision audit events in run timeline.
- Approval API:
  - `GET /v1/approvals`
  - `GET /v1/approvals/{approval_id}`
  - `POST /v1/approvals/{approval_id}/approve`
  - `POST /v1/approvals/{approval_id}/reject`
- Approval CLI:
  - `agent-kernel approval list`
  - `agent-kernel approval inspect <approval-id>`
  - `agent-kernel approval approve <approval-id>`
  - `agent-kernel approval reject <approval-id> --reason "..."`
- Repository tests.
- API tests.
- CLI tests.
- Documentation and milestone updates.

Day 11 should not cover:

- Run `waiting_approval` transition integration.
- Resume execution after approval.
- Rejection stopping a run.
- Retry/fallback.
- Provider-native tool/function calling.
- Agent run loop integration.
- Web UI.
- Auth/authorization enforcement beyond preserving reviewer fields for future use.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Should approval decisions update run status?
  - Proposed: no on Day 11. Persist decisions and audit events first; Day 12 wires run state.
- How are approval requests created?
  - Proposed: repository creates an approval for a persisted `ToolCall` that is waiting approval.
- Should rejected approvals use `decision_note`?
  - Proposed: yes. CLI/API use `reason` as decision note.
- Should duplicate decisions be rejected?
  - Proposed: yes. Only `requested` approvals can be approved or rejected.
- Should API expose creation?
  - Proposed: no. Approval creation is internal to tool/policy flow. API exposes operator workflow.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-11.md`.
- [x] Read `docs/specs/approval-resume.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect current `Approval` domain model.
- [x] Inspect `ToolCallRepository`.
- [x] Add approval decision run event types.
- [x] Add `ApprovalRecord`.
- [x] Add Alembic migration for `approvals`.
- [x] Add `ApprovalRepository`.
- [x] Add approval create/list/get.
- [x] Add approve/reject decision methods.
- [x] Add duplicate decision protection.
- [x] Add run event audit entries.
- [x] Add API schemas.
- [x] Add API routes.
- [x] Add CLI approval commands.
- [x] Add repository tests.
- [x] Add API tests.
- [x] Add CLI tests.
- [x] Update approval spec.
- [x] Update security policy spec if audit semantics change.
- [x] Update milestones.
- [x] Record completion notes in this file.

## Acceptance

- [x] `approvals` table model exists.
- [x] Migration exists.
- [x] Requested approval can be persisted for a tool call.
- [x] Approvals can be listed.
- [x] A single approval can be inspected.
- [x] Approval can be approved.
- [x] Approval can be rejected with a reason.
- [x] Duplicate decisions fail clearly.
- [x] Approval request and decisions append run timeline events.
- [x] API exposes list/get/approve/reject.
- [x] CLI exposes list/inspect/approve/reject.
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
uv run pytest tests/unit/test_approval_repository.py tests/integration/test_api_approvals.py tests/unit/test_cli_commands.py
```

## Notes

- Day 11 is approval persistence and operator interface only.
- Do not resume runs yet.
- Do not stop rejected runs yet.
- Do not add auth yet, but keep reviewer fields in the model.
- Use run events as the audit timeline baseline.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 11：请按照 docs/daily/day-11.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-11.md、docs/specs/approval-resume.md、docs/specs/security-policy.md、docs/specs/tool-calling.md 和 docs/milestones.md。
- 只实现 Day 11 scope 内的内容，不提前做 run waiting_approval integration、resume execution、rejection stopping run、retry/fallback、agent run loop integration、auth、RAG、memory 或 Web UI。
- Approval duplicate decisions 必须被拒绝。
- Approval request/decision 必须写入 run event audit timeline。
- 如果 approval persistence 或 API/CLI 语义变化，更新相关 spec。
- 完成后运行 Day 11 verification commands。
- 更新 docs/daily/day-11.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Added approval run event types:
  - `approval_approved`
  - `approval_rejected`
- Added `ApprovalRecord`.
- Added Alembic migration `0003_create_approvals`.
- Added `ApprovalRepository`.
- Approval requests can be created for persisted tool calls.
- Approval requests update the associated tool call to `waiting_approval`.
- Approvals can be listed and inspected.
- Requested approvals can be approved or rejected.
- Duplicate approval decisions raise `ApprovalDecisionError`.
- Approval request and decision events are appended to the run timeline.
- Added API endpoints for list/get/approve/reject.
- Added CLI commands for list/inspect/approve/reject.
- Added repository, API, and CLI tests.
- Updated approval and security specs.
- Updated Phase 2 milestones for approval model/API/CLI.

Verification passed:

- `uv sync`
- `uv run pytest tests/unit/test_approval_repository.py tests/integration/test_api_approvals.py tests/unit/test_cli_commands.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `uv run alembic upgrade head`
- `docker compose config`
- `pre-commit run --all-files`

Full test result:

- 74 tests passed.
- 1 upstream `StarletteDeprecationWarning` remains from FastAPI/TestClient.

Known caveat:

- Day 11 does not transition runs to `waiting_approval`, resume approved runs, stop rejected runs,
  or enforce authorization. Those belong to the Day 12 interrupt/resume slice.
