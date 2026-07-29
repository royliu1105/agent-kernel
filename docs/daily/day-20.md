# Day 20: kb_search Tool and Agent Runtime Integration

## Goal

Make indexed knowledge bases usable by agent runs through a safe built-in tool.

Day 20 should establish this path:

```text
run input tool request -> kb_search -> retriever -> cited chunks -> run output and tool audit timeline
```

## Scope

Day 20 should cover:

- `kb_search` tool implementation.
- Read-only tool metadata and JSON schemas.
- Tool argument validation for knowledge base ID, query, and top-k.
- Tool output containing query, model, ranked results, and citations.
- Runtime composition so API-created/resumed runs and worker-executed runs can use `kb_search`.
- Tests for tool execution.
- Tests for explicit agent run integration with `kb_search`.
- Worker integration coverage for queued `kb_search` runs.
- RAG spec, milestone, and daily index updates.

Day 20 should not cover:

- Provider-native function calling.
- Automatic model planning to decide when to call `kb_search`.
- Persisted retrieval call records separate from existing tool calls.
- Memory.
- RAG behavior eval suites.
- RRF.
- BM25 keyword search.
- Hybrid search.
- Reranking.
- Query rewriting.

## Domain Terms

- `kb_search`: safe read-only built-in tool that searches one knowledge base.
- Explicit tool request: current runtime path where run input contains `tool.name` and `tool.arguments`.
- Tool audit timeline: persisted `tool_calls` records and run events created by existing runtime execution.

## Tasks

- [x] Check current git status.
- [x] Read Day 20 plan, RAG spec, tool runtime, worker, and retrieval code.
- [x] Create Day 20 daily plan.
- [x] Add `kb_search` tool.
- [x] Add helper for a RAG-aware tool registry.
- [x] Wire API runtime composition to include `kb_search`.
- [x] Wire worker runtime composition to include `kb_search`.
- [x] Add unit tests for `kb_search`.
- [x] Add runtime tests for explicit `kb_search` run execution.
- [x] Add worker tests for queued `kb_search` run execution.
- [x] Update RAG spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] `kb_search` is registered as a read-only tool.
- [x] `kb_search` validates `knowledge_base_id`, `query`, and `top_k`.
- [x] `kb_search` returns cited retrieval results.
- [x] A run can execute an explicit `kb_search` tool request.
- [x] The run output includes the tool result.
- [x] Tool call audit records persist the `kb_search` request and result.
- [x] Queued runs executed by the worker can use `kb_search`.
- [x] Day 20 does not implement provider-native function calling, automatic planning, memory, RRF, BM25, hybrid search, or reranking.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_kb_search_tool.py tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py
```

## Notes

- `kb_search` should live beside RAG retrieval code because it depends on storage-backed retrieval.
- The base `kernel-tools` package should remain storage-agnostic.
- Day 20 uses explicit tool requests only; model-native tool choice comes later.

## Completion Notes

- Added `KnowledgeBaseSearchTool` as a read-only RAG-backed tool.
- Added `create_rag_tool_registry` to compose default tools with `kb_search`.
- Wired API and worker runtime composition to register `kb_search`.
- Added focused tests for direct tool execution, explicit runtime execution, and queued worker execution.
- Updated RAG spec, milestones, and daily plan index.
- Confirmed Day 20 does not implement provider-native function calling, automatic planning, memory, RRF, BM25, hybrid search, reranking, or query rewriting.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 20：请按照 docs/daily/day-20.md 执行 kb_search Tool and Agent Runtime Integration。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-20.md、docs/specs/rag.md、现有 tool/runtime/worker/retrieval 代码和测试。
- 只实现 Day 20 scope 内的内容。
- 今天只做 run input tool request -> kb_search -> retriever -> cited chunks -> run output and tool audit timeline。
- 不做 provider-native function calling、automatic planning、persisted retrieval calls、memory、RAG behavior eval suite、RRF、BM25、hybrid search、reranking 或 query rewriting。
- kb_search 必须是 read-only tool。
- API 和 worker 的 runtime composition 都要注册 kb_search。
- 完成后运行 Day 20 verification commands。
- 更新 docs/daily/day-20.md 的 checklist。
- 更新 RAG spec 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
