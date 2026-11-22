# Day 47: Behavior Eval Coverage Expansion

## Goal

Expand cheap deterministic behavior eval coverage for RAG retrieval regressions
before Public Alpha closure.

## Scope

- Add result-count upper-bound assertions.
- Add top-result score assertions.
- Add citation source URI assertions.
- Extend file-backed RAG dataset parsing.
- Update the default cheap RAG eval fixture.
- Update eval spec and Public Alpha milestone.

## Tasks

- [x] Create Day 47 daily plan.
- [x] Add `max_results` support to RAG eval cases.
- [x] Add `min_top_score` support to RAG eval cases.
- [x] Add `citation_source_uri_must_contain` support to RAG eval cases.
- [x] Extend JSON dataset loading and validation.
- [x] Add unit tests for passing and failing behavior assertions.
- [x] Update `evals/rag-smoke.json`.
- [x] Update eval spec and milestones.

## Acceptance

- [x] RAG evals can assert retrieval returns no more than an expected number of
  results.
- [x] RAG evals can assert a minimum top-result score.
- [x] RAG evals can assert citation source URI terms.
- [x] Failure reports identify the failed behavior assertion by name.
- [x] Existing eval datasets remain backward compatible.

## Verification

- [x] `git diff --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_rag_evals.py`
- [x] `uv run pytest tests/unit/test_cli_commands.py`
- [x] `uv run agent-kernel eval report evals/rag-smoke.json`

## Notes

- Day 47 does not implement persisted eval runs.
- Day 47 does not add an eval API, LLM-as-judge, real-model CI evals, Web eval
  authoring, or release-blocking eval suites.
