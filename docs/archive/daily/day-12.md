# Day 12: Approval Interrupt and Resume

## Goal

Connect approval decisions to durable run execution state.

Day 12 should establish this path:

```text
risky tool requested -> policy requires approval -> approval requested -> run waiting_approval
approval approved -> run resuming -> tool executes -> run succeeded
approval rejected -> run failed
```

This closes the Phase 2 human-in-the-loop MVP path. Retry/fallback remains a separate slice.

## Scope

Day 12 should cover:

- Phase 2 planning alignment.
- Approval/resume spec refinement.
- Run state machine helpers for waiting approval and resuming.
- Runtime execution support for explicit single-tool run input.
- Persisting risky tool calls before approval.
- Creating approval requests from policy decisions.
- Transitioning runs to `waiting_approval`.
- Resuming approved runs.
- Executing the approved tool with the original persisted arguments.
- Completing the run with the tool result.
- Failing the run when approval is rejected.
- Preventing resume from missing, undecided, unrelated, or invalid approvals.
- Worker behavior for waiting/resuming runs.
- API endpoint for run resume.
- CLI command for run resume.
- Unit and integration tests.
- Documentation and milestone updates.

Day 12 should not cover:

- Retry/fallback.
- Provider-native function calling.
- Model-generated tool call parsing.
- Multi-step agent loops.
- Multi-agent handoff.
- Web UI approval inbox.
- Auth/authorization enforcement.
- Arbitrary shell, network, or filesystem write tools.

## Input Contract

Until provider-native tool calling is added, Day 12 uses an explicit tool request in run input:

```json
{
  "tool": {
    "name": "echo",
    "arguments": {
      "message": "hello"
    }
  }
}
```

Optional fields:

```json
{
  "tool": {
    "name": "echo",
    "arguments": {},
    "model": "mock:mock-default"
  }
}
```

If no `tool` object is present, the existing model-call execution path remains unchanged.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-12.md`.
- [x] Read `docs/specs/approval-resume.md`.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect runtime execution, worker, state machine, policy, tool executor, and repositories.
- [x] Add state machine helpers for wait/resume.
- [x] Add repository support needed for resume/fail transitions.
- [x] Add runtime explicit-tool execution path.
- [x] Add approval-required interrupt path.
- [x] Add approved resume execution path.
- [x] Add rejected approval fail path.
- [x] Add API resume endpoint.
- [x] Add CLI run resume command.
- [x] Add execution tests.
- [x] Add worker tests.
- [x] Add API tests.
- [x] Add CLI tests.
- [x] Update approval/resume spec.
- [x] Update run lifecycle spec.
- [x] Update tool-calling spec.
- [x] Update security policy spec if audit semantics change.
- [x] Update milestones.
- [x] Record completion notes in this file.

## Acceptance

- [x] Safe explicit tool runs execute and succeed.
- [x] Risky explicit tool runs transition to `waiting_approval`.
- [x] Risky explicit tool runs create a persisted approval.
- [x] Waiting runs are not picked as queued work.
- [x] Approved runs can resume and succeed.
- [x] Rejected approvals fail the run safely.
- [x] Resume cannot proceed for requested or missing approvals.
- [x] Resume uses the original persisted tool call arguments.
- [x] API exposes run resume.
- [x] CLI exposes run resume.
- [x] Approval and resume actions are visible in run events.
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
uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py tests/integration/test_api_run_lifecycle.py tests/unit/test_cli_commands.py
```

## Notes

- Day 12 keeps the explicit-tool input shape intentionally small.
- Day 12 does not add model-generated function calling.
- Approval decisions are already persisted by Day 11.
- Resume must execute the persisted tool call, not caller-supplied new arguments.

## Completion Notes

- Added run transition events:
  - `run_waiting_approval`
  - `run_resuming`
- Added state machine helpers:
  - `wait_for_approval`
  - `resume`
- Added `RunRepository.session` so runtime orchestration can share one transaction/session scope
  with tool call and approval repositories.
- Added `ToolCallRepository.mark_running`.
- Added `ApprovalRepository.list_for_run`.
- Added `create_default_tool_registry` with the safe `echo` built-in.
- `RunExecutionService` now supports explicit single-tool input under `input.tool`.
- Safe explicit tools are policy-checked, executed, persisted, and returned under `output.tool`.
- Approval-required explicit tools create a tool call, create approval, and pause the run at
  `waiting_approval`.
- Approved resume executes the original persisted tool call arguments and completes the run.
- Rejected resume fails the waiting run with `approval_rejected`.
- Added `POST /v1/runs/{run_id}/resume`.
- Added `agent-kernel run resume <run-id> --approval-id <approval-id>`.
- Updated approval/resume, run lifecycle, tool calling, and security policy specs.
- Updated Phase 2 milestones for interrupt/resume acceptance.

Verification passed:

- `uv sync`
- `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py tests/integration/test_api_run_lifecycle.py tests/unit/test_cli_commands.py tests/unit/test_run_state_machine.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `docker compose config`
- `pre-commit run --all-files`

Full test result:

- 84 tests passed.
- 1 upstream `StarletteDeprecationWarning` remains from FastAPI/TestClient.

Known caveat:

- Day 12 still does not implement retry/fallback, provider-native function calling, multi-step
  agent loops, Web UI approval inbox, or auth enforcement.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 12：请按照 docs/daily/day-12.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-12.md、docs/specs/approval-resume.md、docs/specs/run-lifecycle.md、docs/specs/tool-calling.md、docs/specs/security-policy.md 和 docs/milestones.md。
- 只实现 Day 12 scope 内的内容，不提前做 retry/fallback、provider-native function calling、agent run loop、auth、RAG、memory 或 Web UI。
- Risky explicit tool 必须暂停 run 并创建 approval。
- Approved approval 必须恢复并执行原始 persisted tool call。
- Rejected approval 必须让 run 安全失败。
- Resume 不能接受新的 tool arguments。
- 行为或架构语义变化时，更新对应 spec。
- 完成后运行 Day 12 verification commands。
- 更新 docs/daily/day-12.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
