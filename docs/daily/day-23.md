# Day 23: Memory Retrieval and Agent Context Integration

## Goal

Make scoped memory usable by model runs without making memory behavior implicit or opaque.

Day 23 should establish this path:

```text
run input memory config -> scoped memory retrieval -> system context injection -> run output/timeline visibility
```

## Scope

Day 23 should cover:

- Memory retrieval service for scoped memory records.
- Optional filtering by memory type.
- Limit handling for retrieved memory items.
- Runtime parsing for explicit memory config in run input.
- Agent context injection through a system message.
- Run timeline visibility when memory retrieval is requested.
- Run output metadata showing memory item IDs used.
- Tests for memory retrieval behavior.
- Tests for model request context injection.
- Tests for invalid memory config.
- Memory spec, milestone, and daily index updates.

Day 23 should not cover:

- Automatic memory writes.
- Semantic/vector memory retrieval.
- Memory consolidation.
- Graph memory.
- LLM-based memory selection.
- Conflict resolution between current instructions and stored memory.
- Provider-native function calling.
- Memory observability spans.

## Runtime Input Shape

Memory is explicit opt-in through run input:

```json
{
  "task": "Summarize this for me.",
  "memory": {
    "scopes": ["user:roy", "task:deploy"],
    "types": ["user_preference", "task_context"],
    "limit": 10
  }
}
```

Rules:

- `memory.scopes` is required when `memory` is present.
- `memory.scopes` must be a non-empty list of non-empty strings.
- `memory.types` is optional and must contain valid `MemoryType` values when present.
- `memory.limit` is optional and defaults to `10`.
- Memory is injected only into model runs, not explicit tool-only runs.

## Tasks

- [x] Check current git status.
- [x] Read Day 23 plan, memory spec, runtime execution code, memory repository, and tests.
- [x] Create Day 23 daily plan.
- [x] Add memory retrieval service.
- [x] Add prompt/context rendering for memory items.
- [x] Add runtime memory config parsing.
- [x] Inject memory context into model request messages.
- [x] Add memory retrieved run event.
- [x] Add memory metadata to model run output.
- [x] Add memory retrieval unit tests.
- [x] Add runtime memory context tests.
- [x] Add invalid memory config tests.
- [x] Update memory spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] Memory can be retrieved by one or more scopes.
- [x] Memory can be filtered by memory type.
- [x] Retrieved memory is rendered into model context.
- [x] Runtime records memory retrieval visibility in run events.
- [x] Runtime output includes memory item IDs used.
- [x] Invalid memory config fails clearly.
- [x] Day 23 does not implement automatic memory writes, semantic/vector memory retrieval, consolidation, graph memory, LLM memory selection, conflict resolution, provider-native function calling, or memory observability spans.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_memory_retrieval.py tests/unit/test_runtime_execution.py
```

## Notes

- Runtime memory use is explicit so current user instructions remain easier to reason about.
- Day 23 uses exact scope/type filtering, not semantic recall.
- Day 24 will summarize known limitations and close Phase 3.

## Completion Notes

- Added `MemoryRetrievalService` and `MemoryContext`.
- Added deterministic memory prompt rendering.
- Added explicit runtime memory config parsing through `run.input.memory`.
- Injected retrieved memory as a system message for model runs.
- Added `memory_retrieved` run event visibility.
- Added memory usage metadata to model run output.
- Added memory retrieval and runtime context tests.
- Updated memory spec, milestones, and daily plan index.
- Confirmed Day 23 does not implement automatic memory writes, semantic/vector retrieval, consolidation, graph memory, LLM memory selection, conflict resolution, provider-native function calling, or memory observability spans.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 23：请按照 docs/daily/day-23.md 执行 Memory Retrieval and Agent Context Integration。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-23.md、docs/specs/memory.md、runtime execution、memory repository 和相关测试。
- 只实现 Day 23 scope 内的内容。
- 今天只做 run input memory config -> scoped memory retrieval -> system context injection -> run output/timeline visibility。
- 不做 automatic memory writes、semantic/vector memory retrieval、memory consolidation、graph memory、LLM-based memory selection、conflict resolution、provider-native function calling 或 observability spans。
- memory 使用必须是显式 opt-in。
- 完成后运行 Day 23 verification commands。
- 更新 docs/daily/day-23.md 的 checklist。
- 更新 memory spec 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
