# Day 09: Policy Decisions for Tool Execution

## Goal

Add the first policy layer above the Day 8 tool executor.

Day 9 should establish this path:

```text
tool request -> registry metadata -> policy evaluation -> allow / deny / require approval
```

For allowed tools, execution can continue through the existing `ToolExecutor`. For denied or
approval-required tools, execution must stop before the tool runs.

## Scope

Day 9 should cover:

- Phase 2 planning alignment.
- Security policy spec refinement.
- `kernel-policy` package implementation.
- `PolicyDecision` model.
- `PolicyDecisionType` enum.
- `ToolPolicy` model.
- Policy evaluator.
- Rule precedence for tool names and risk levels.
- Default policy behavior.
- Policy-aware tool execution wrapper or service.
- Tests for safe tool allow.
- Tests for denied tool not executing.
- Tests for approval-required tool not executing.
- Tests for explicit tool-name overrides.
- Tests for risk-level decisions.
- Documentation updates.
- Milestone updates for completed Phase 2 items.

Day 9 should not cover:

- Approval persistence.
- Approval API or CLI.
- Run lifecycle `waiting_approval` integration.
- Interrupt/resume.
- Persisted `ToolCall` records.
- Audit log persistence.
- Agent run loop integration.
- Provider-native tool/function calling.
- Retry/fallback.
- Network, shell, filesystem write, or other side-effecting built-in tools.
- Web UI.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- What are the Day 9 policy decisions?
  - Proposed: `allow`, `deny`, `require_approval`.
- What does the default policy do?
  - Proposed: allow `read_only`, require approval for `external_write`, `filesystem_write`, and
    `network`, deny `dangerous`.
- How should explicit tool-name overrides work?
  - Proposed: tool-name rules override risk-level defaults.
- Should approval-required calls create approvals on Day 9?
  - Proposed: no. Day 9 returns a typed policy result; Day 10/11 can persist tool calls and create
    approvals.
- Where should policy-aware execution live?
  - Proposed: in `kernel-policy`, depending on `kernel-tools`, as a small service that evaluates
    policy before delegating to `ToolExecutor` for allowed calls.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-09.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/specs/approval-resume.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect `kernel-policy` package.
- [x] Inspect `kernel-tools` executor and errors.
- [x] Decide policy model and precedence.
- [x] Add policy decision enum/model.
- [x] Add tool policy model.
- [x] Add policy evaluator.
- [x] Add policy-aware execution service.
- [x] Add tests for read-only safe tool allow and execution.
- [x] Add tests for denied tool not executing.
- [x] Add tests for approval-required tool not executing.
- [x] Add tests for explicit tool-name override precedence.
- [x] Add tests for risk-level default decisions.
- [x] Update `docs/specs/security-policy.md`.
- [x] Update `docs/specs/tool-calling.md` if execution flow changes.
- [x] Update `docs/milestones.md` Phase 2 progress.
- [x] Record completion notes in this file.

## Acceptance

- [x] Policy decision types exist.
- [x] Tool policy model exists.
- [x] Policy evaluator exists.
- [x] Default policy allows `read_only` tools.
- [x] Default policy requires approval for write/network tools.
- [x] Default policy denies `dangerous` tools.
- [x] Explicit tool-name policy overrides risk-level defaults.
- [x] Allowed safe tool executes through policy-aware service.
- [x] Denied tools do not execute.
- [x] Approval-required tools do not execute on Day 9.
- [x] Tests remain deterministic and do not use network.
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
uv run pytest tests/unit/test_policy.py
```

## Notes

- Day 9 adds policy decisions, not approval workflows.
- Approval-required means "pause before execution", not "create persisted approval" yet.
- Do not execute denied or approval-required tools.
- Keep policy explicit and small. Do not add OPA/Rego.
- Keep default policy conservative.
- Do not add side-effecting built-in tools.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 9：请按照 docs/daily/day-09.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-09.md、docs/specs/security-policy.md、docs/specs/tool-calling.md、docs/specs/approval-resume.md 和 docs/milestones.md。
- 只实现 Day 9 scope 内的内容，不提前做 approval persistence、approval API/CLI、run waiting_approval integration、interrupt/resume、persisted ToolCall、audit log persistence、agent run loop integration、retry/fallback、RAG、memory 或 Web UI。
- Deny 和 require_approval 都不能执行工具。
- 默认策略必须 conservative：read_only allow，dangerous deny，写/网络类 require_approval。
- 自动化测试不能真实访问网络，也不能要求 API key。
- 如果 policy decision 或 tool execution flow 语义变化，更新相关 spec。
- 完成后运行 Day 9 verification commands。
- 更新 docs/daily/day-09.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Implemented `kernel-policy` package baseline.
- Added:
  - `PolicyDecisionType`
  - `PolicyDecision`
  - `ToolPolicy`
  - `ToolPolicyEvaluator`
  - `PolicyAwareToolExecutor`
  - `ToolDeniedError`
  - `ToolApprovalRequiredError`
- Added conservative default risk policy:
  - `read_only` -> `allow`
  - `external_write` -> `require_approval`
  - `filesystem_write` -> `require_approval`
  - `network` -> `require_approval`
  - `dangerous` -> `deny`
- Explicit tool-name rules override risk-level defaults.
- Allowed tools execute through `ToolExecutor`.
- Denied tools do not execute.
- Approval-required tools do not execute on Day 9.
- Added `tests/unit/test_policy.py`.
- Updated security policy and tool calling specs.
- Updated Phase 2 milestone progress.

Verification passed:

- `uv sync`
- `uv run pytest tests/unit/test_policy.py tests/unit/test_tools.py`
- `uv run ruff check .`
- `uv run mypy .`

Known caveat:

- Day 9 does not persist policy decisions, create audit events, create approval records, or move
  runs to `waiting_approval`. That belongs to the approval/persistence slices.
