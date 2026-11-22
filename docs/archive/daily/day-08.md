# Day 08: Tool Interface and Safe Execution Foundation

## Goal

Start Phase 2 by introducing the first production-shaped tool calling foundation.

Day 8 should establish the safe, deterministic core path:

```text
tool definition -> registry -> JSON schema validation -> executor -> typed result
```

This is not yet full agent tool calling inside the run loop. The goal is to build the tool boundary
that policy, approval, audit, and runtime integration can rely on.

## Scope

Day 8 should cover:

- Phase 2 planning alignment.
- Tool calling spec refinement.
- Security policy spec refinement if risk-level semantics are clarified.
- `kernel-tools` package implementation.
- Tool metadata model.
- Tool request/result model.
- Tool error model.
- Tool interface or protocol.
- Tool registry.
- JSON schema input validation.
- Tool executor.
- Timeout boundary if it can stay simple and deterministic.
- Result size limit baseline if it can stay simple.
- Built-in safe read-only tool.
- Tests for registry behavior.
- Tests for schema validation.
- Tests for successful tool execution.
- Tests for unknown tool handling.
- Tests for tool failure handling.
- Tests for timeout or size limit only if implemented.
- Documentation updates.
- Milestone updates for completed Phase 2 items.

Day 8 should not cover:

- Provider-native tool/function calling.
- Agent run loop integration.
- Persisted `ToolCall` records.
- Tool call timeline events.
- Policy engine decisions beyond risk metadata.
- Human approval.
- Interrupt/resume.
- Retry/fallback.
- Arbitrary shell execution.
- Network tools.
- Filesystem write tools.
- Web UI.
- RAG or memory tools.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- What is the minimal tool contract?
  - Proposed: async protocol with `name`, `description`, `input_schema`, `risk_level`, and
    `execute(arguments)`.
- Should tool schema validation use `jsonschema`?
  - Proposed: yes if dependency impact is small. Otherwise use `pydantic` for Day 8 and document
    the limitation. Prefer a real JSON Schema validator if available.
- What is the first built-in safe tool?
  - Proposed: deterministic `echo` or `time` style read-only tool. Avoid filesystem and network.
- Should Day 8 persist tool calls?
  - Proposed: no. Persistence belongs after the contract and executor are stable.
- Should Day 8 integrate tools into `RunExecutionService`?
  - Proposed: no. Provider-native tool calling and runtime loop integration should happen after the
    executor and policy boundary exist.
- How should risk levels be represented?
  - Proposed: reuse the existing `RiskLevel` domain enum from `kernel-core` if dependency direction
    remains clean.

## Tasks

- [x] Check current git status.
- [x] Read `docs/daily/day-08.md`.
- [x] Read `docs/specs/tool-calling.md`.
- [x] Read `docs/specs/security-policy.md`.
- [x] Read `docs/specs/approval-resume.md`.
- [x] Read `docs/milestones.md` Phase 2 section.
- [x] Inspect existing `kernel-tools` package.
- [x] Inspect existing `kernel-policy` package.
- [x] Decide minimal tool contract and validation approach.
- [x] Add tool metadata/request/result/error models.
- [x] Add tool protocol or base interface.
- [x] Add tool registry.
- [x] Add schema validation.
- [x] Add tool executor.
- [x] Add one safe built-in read-only tool.
- [x] Add tests for registering and retrieving tools.
- [x] Add tests for duplicate registration.
- [x] Add tests for unknown tools.
- [x] Add tests for invalid arguments.
- [x] Add tests for successful safe tool execution.
- [x] Add tests for tool-raised errors.
- [x] Add timeout or result-size tests if those boundaries are implemented.
- [x] Update `docs/specs/tool-calling.md`.
- [x] Update `docs/specs/security-policy.md` if risk semantics change.
- [x] Update `docs/milestones.md` Phase 2 progress.
- [x] Record completion notes in this file.

## Acceptance

- [x] A typed tool contract exists.
- [x] A tool registry exists.
- [x] Duplicate tool registration fails clearly.
- [x] Unknown tool lookup/execution fails clearly.
- [x] Tool arguments are validated before execution.
- [x] Invalid arguments do not execute the tool.
- [x] A safe built-in read-only tool can execute deterministically.
- [x] Tool errors are converted to typed execution errors.
- [x] Tool risk level is represented in metadata.
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
uv run pytest tests/unit/test_tools.py
```

## Notes

- Day 8 is about the tool boundary, not the full agent tool loop.
- Keep the first built-in tool boring and safe.
- Do not add arbitrary shell execution.
- Do not add network or filesystem write tools.
- Policy should see tool risk metadata later; Day 8 does not need a real policy engine.
- Approval and persisted tool calls start after executor behavior is stable.
- Prefer explicit typed errors over returning ad hoc dictionaries.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 8：请按照 docs/daily/day-08.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-08.md、docs/specs/tool-calling.md、docs/specs/security-policy.md、docs/specs/approval-resume.md 和 docs/milestones.md。
- 只实现 Day 8 scope 内的内容，不提前做 provider-native tool calling、agent run loop integration、policy engine、human approval、interrupt/resume、retry/fallback、RAG、memory 或 Web UI。
- 默认内置工具必须 safe/read-only/deterministic，不能访问网络，不能写文件，不能执行 shell。
- 自动化测试不能真实访问网络，也不能要求 API key。
- 如果工具接口、schema validation 或 risk level 语义变化，更新相关 spec。
- 完成后运行 Day 8 verification commands。
- 更新 docs/daily/day-08.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```

## Completion Notes

- Implemented `kernel-tools` package baseline.
- Added typed tool models:
  - `ToolMetadata`
  - `ToolRequest`
  - `ToolResult`
- Added typed tool errors:
  - `DuplicateToolError`
  - `UnknownToolError`
  - `ToolDisabledError`
  - `ToolValidationError`
  - `ToolExecutionFailedError`
  - `ToolTimeoutError`
  - `ToolResultTooLargeError`
- Added async `Tool` protocol.
- Added in-memory `ToolRegistry`.
- Added `ToolExecutor`.
- Added JSON Schema argument validation through `jsonschema`.
- Added timeout handling through `asyncio.wait_for`.
- Added JSON object and serialized result size boundaries.
- Added deterministic safe `EchoTool` with `read_only` risk level.
- Added `tests/unit/test_tools.py`.
- Updated tool calling and security policy specs.
- Updated Phase 2 milestone progress for tool foundation items.

Verification passed:

- `uv sync`
- `uv run pytest tests/unit/test_tools.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

Known caveat:

- Day 8 does not integrate tools into the agent run loop, persist tool calls, evaluate policy, or
  request approvals. Those start after the tool executor boundary is stable.
