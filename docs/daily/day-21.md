# Day 21: RAG Behavior Evals and Regression Cases

## Goal

Add deterministic RAG behavior evals so retrieval and `kb_search` regressions are caught before later phases build on top of them.

Day 21 should establish this path:

```text
eval case -> retrieval callable -> assertion checks -> eval report
```

## Scope

Day 21 should cover:

- Minimal eval result/report domain models.
- RAG eval case model.
- RAG eval runner.
- Assertions for retrieval relevance.
- Assertions for required citations.
- Assertions for empty knowledge base behavior.
- Assertions for expected retrieval errors.
- Regression tests that exercise real retriever behavior.
- Regression tests that exercise `kb_search` tool behavior where useful.
- Evals spec, RAG spec, milestone, and daily index updates.

Day 21 should not cover:

- Full eval API.
- Full eval CLI.
- Persisted eval runs.
- LLM-as-judge.
- Public benchmark datasets.
- Cost and latency dashboards.
- Memory evals.
- RRF.
- BM25 keyword search.
- Hybrid search.
- Reranking.
- Query rewriting.

## Domain Terms

- Eval case: deterministic scenario with expected retrieval behavior.
- Eval assertion: one check inside a case, such as "top result contains rollback" or "citation exists".
- Eval report: aggregate pass/fail result across eval cases.
- RAG behavior eval: retrieval-specific eval focused on relevance, citations, empty results, and error behavior.

## Tasks

- [x] Check current git status.
- [x] Read Day 21 plan, evals spec, RAG spec, retrieval code, and `kb_search` code.
- [x] Create Day 21 daily plan.
- [x] Add eval result/report models.
- [x] Add RAG eval case model.
- [x] Add RAG eval runner.
- [x] Add retrieval relevance assertions.
- [x] Add citation presence assertions.
- [x] Add empty knowledge base assertions.
- [x] Add expected error assertions.
- [x] Add unit tests for RAG evals.
- [x] Update evals spec.
- [x] Update RAG spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] A passing RAG eval case can assert relevant content appears in retrieved results.
- [x] A passing RAG eval case can assert cited results include source identity.
- [x] A failing RAG eval case records assertion-level failure reasons.
- [x] Empty knowledge base behavior can be evaluated deterministically.
- [x] Missing knowledge base behavior can be evaluated deterministically.
- [x] Eval reports include passed/failed counts.
- [x] Day 21 does not implement full eval API/CLI, persistence, LLM-as-judge, memory evals, RRF, BM25, hybrid search, or reranking.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_rag_evals.py tests/unit/test_retrieval.py tests/unit/test_kb_search_tool.py
```

## Notes

- Eval implementation should remain cheap enough for default CI.
- Day 21 should establish useful APIs without pretending to be the full Phase 4 eval platform.
- Failure reasons should be human-readable because they are teaching and maintenance tools.

## Completion Notes

- Added eval result/report models.
- Added deterministic `RagEvalCase` and `RagEvalRunner`.
- Added assertions for minimum result count, top-result content, citations, empty knowledge bases, and expected retrieval errors.
- Added regression tests over real `Retriever` behavior.
- Updated evals spec, RAG spec, milestones, and daily plan index.
- Confirmed Day 21 does not implement full eval API/CLI, persisted eval runs, LLM-as-judge, memory evals, RRF, BM25, hybrid search, reranking, or query rewriting.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 21：请按照 docs/daily/day-21.md 执行 RAG Behavior Evals and Regression Cases。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-21.md、docs/specs/evals.md、docs/specs/rag.md、retrieval 和 kb_search 相关代码。
- 只实现 Day 21 scope 内的内容。
- 今天只做 eval case -> retrieval callable -> assertion checks -> eval report。
- 不做 full eval API/CLI、persisted eval runs、LLM-as-judge、public benchmark、memory evals、RRF、BM25、hybrid search、reranking 或 query rewriting。
- eval 必须 deterministic、cheap、CI-friendly。
- failure reason 必须清楚可读。
- 完成后运行 Day 21 verification commands。
- 更新 docs/daily/day-21.md 的 checklist。
- 更新 evals spec、RAG spec 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
