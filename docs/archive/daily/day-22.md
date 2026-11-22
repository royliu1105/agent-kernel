# Day 22: Memory Domain, Storage, API, and CLI

## Goal

Add the explicit memory foundation so users and operators can write, inspect, list, and delete scoped memory items.

Day 22 should establish this path:

```text
memory create -> persisted scoped memory item -> list/inspect/delete through API and CLI
```

## Scope

Day 22 should cover:

- `MemoryType` enum.
- `MemoryItem` domain model.
- Required memory scope.
- Structured JSON memory content.
- Optional `source_run_id`.
- Confidence score.
- Memory metadata.
- Memory storage table and Alembic migration.
- Memory repository create/list/get/delete operations.
- Memory API schemas and endpoints.
- Memory CLI commands.
- Unit tests for memory model and repository.
- API integration tests for memory CRUD.
- CLI tests for memory commands.
- Memory spec, milestone, and daily index updates.

Day 22 should not cover:

- Agent context injection.
- Semantic memory retrieval.
- Vector memory search.
- Automatic memory writes.
- Memory consolidation.
- Graph memory.
- Conflict resolution between memory and current instructions.
- Memory observability spans.

## Domain Terms

- Memory item: one persisted memory record.
- Memory type: one of `short_term`, `task_context`, `user_preference`, or `long_term`.
- Scope: required boundary string such as `user:123`, `task:abc`, or `agent:<agent-id>`.
- Source run: optional run ID that explains where the memory came from.

## Tasks

- [x] Check current git status.
- [x] Read Day 22 plan, memory spec, storage/API/CLI patterns, and tests.
- [x] Create Day 22 daily plan.
- [x] Add `MemoryType` and `MemoryItem` domain models.
- [x] Add memory storage model.
- [x] Add memory Alembic migration.
- [x] Add memory repository.
- [x] Export memory storage APIs.
- [x] Add memory API schemas.
- [x] Add memory API endpoints.
- [x] Add memory CLI commands.
- [x] Add unit tests.
- [x] Add API integration tests.
- [x] Add CLI tests.
- [x] Update memory spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] A memory item can be created with type, scope, content, confidence, source run, and metadata.
- [x] Memory items can be listed by scope.
- [x] Memory items can be listed by type.
- [x] One memory item can be inspected by ID.
- [x] One memory item can be deleted by ID.
- [x] Missing memory items return not-found behavior.
- [x] CLI can create, list, inspect, and delete memory through the API.
- [x] Day 22 does not implement agent context injection, semantic retrieval, vector search, automatic memory writes, memory consolidation, graph memory, or memory observability spans.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_core_models.py tests/unit/test_memory_repository.py tests/unit/test_cli_commands.py tests/integration/test_api_memory.py
```

## Notes

- Memory content is a JSON object so preferences and task context remain structured.
- Scope is intentionally a string in Day 22 to avoid prematurely designing tenancy and auth policy.
- Day 23 will decide how scoped memory is retrieved and injected into agent context.

## Completion Notes

- Added `MemoryType` and `MemoryItem` domain models.
- Added `memory_items` storage model and Alembic migration.
- Added `MemoryRepository` create/list/get/delete operations.
- Added `/v1/memory` create/list/inspect/delete API endpoints.
- Added `agent-kernel memory create/list/inspect/delete` CLI commands.
- Added core model, repository, API, and CLI tests.
- Updated memory spec, milestones, and daily plan index.
- Confirmed Day 22 does not implement agent context injection, semantic retrieval, vector search, automatic memory writes, memory consolidation, graph memory, or memory observability spans.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 22：请按照 docs/daily/day-22.md 执行 Memory Domain, Storage, API, and CLI。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-22.md、docs/specs/memory.md、storage/API/CLI patterns 和相关测试。
- 只实现 Day 22 scope 内的内容。
- 今天只做 memory create -> persisted scoped memory item -> list/inspect/delete through API and CLI。
- 不做 agent context injection、semantic memory retrieval、vector memory search、automatic memory writes、memory consolidation、graph memory、conflict resolution 或 observability spans。
- Memory scope 必填。
- Memory content 使用 JSON object。
- 完成后运行 Day 22 verification commands。
- 更新 docs/daily/day-22.md 的 checklist。
- 更新 memory spec 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
