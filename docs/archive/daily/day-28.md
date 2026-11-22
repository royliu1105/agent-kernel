# Day 28: Retrieval Metrics and RAG Eval Dataset Runner

## Goal

Add retrieval metrics and a file-backed deterministic RAG eval dataset runner.

Day 28 should establish this observability/eval baseline:

```text
retrieval -> latency/result metrics -> JSON eval dataset -> eval report
```

## Scope

Day 28 should cover:

- Retrieval latency metrics.
- Retrieval count metrics.
- Retrieval result count observations.
- Retrieval failure metrics.
- Optional metrics recorder injection into `Retriever`.
- JSON RAG eval dataset format.
- Dataset validation with readable errors.
- File-backed RAG eval runner helper.
- Tests for retrieval metrics.
- Tests for dataset loading and eval report generation.
- Observability and eval spec updates.

Day 28 should not cover:

- YAML dataset loading.
- Full eval API.
- Full eval CLI.
- Persisted eval runs.
- LLM-as-judge.
- Agent behavior evals beyond existing deterministic RAG retrieval.
- Prometheus/OTel exporters.
- Web UI eval reports.

## Tasks

- [x] Check current git status.
- [x] Read Phase 4 milestones, observability spec, eval spec, RAG eval code, and retriever code.
- [x] Create Day 28 daily plan.
- [x] Add retrieval metrics to `Retriever`.
- [x] Add JSON RAG eval dataset models and loader.
- [x] Add file-backed RAG eval runner helper.
- [x] Add retrieval metrics tests.
- [x] Add eval dataset loader and runner tests.
- [x] Update observability and eval specs.
- [x] Update daily index and milestones.
- [x] Run focused tests.
- [x] Run quality checks.

## Acceptance

- [x] Successful retrieval records retrieval count, latency, and result count metrics.
- [x] Failed retrieval records retrieval failure count and latency metrics.
- [x] Default retriever still works without a configured metrics recorder.
- [x] A JSON RAG eval dataset can be loaded from disk.
- [x] Invalid datasets fail with readable validation errors.
- [x] Loaded datasets can be executed by the RAG eval runner.
- [x] Day 28 does not add YAML loading, persisted eval runs, LLM-as-judge, full eval API/CLI, or UI reports.

## Verification

Run:

```bash
uv run pytest tests/unit/test_retrieval.py tests/unit/test_rag_evals.py tests/unit/test_observability.py
uv run ruff check .
uv run mypy .
git diff --check
```

## Notes

- Keep retrieval metric labels low-cardinality: embedding model, status, and error type.
- Keep dataset format explicit JSON for now.
- Keep eval reports in memory for Day 28; persistence belongs to a later eval platform step.

## Completion Notes

- Added retrieval metrics to `Retriever`.
- Added RAG retrieval success metrics for count, latency, and result count.
- Added RAG retrieval failure metrics for count and latency.
- Added optional metrics recorder injection while keeping default no-op behavior.
- Added JSON RAG eval dataset loading.
- Added readable dataset validation errors.
- Added `RagEvalDataset.run(retrieve)` for file-backed deterministic reports.
- Updated observability and eval specs.
- Updated Phase 4 milestone progress.
- Kept YAML loading, full eval API/CLI, persisted eval runs, LLM-as-judge,
  broader agent behavior evals, Prometheus/OTel exporters, and Web UI eval
  reports deferred.

Verification passed:

- `uv run pytest tests/unit/test_retrieval.py tests/unit/test_rag_evals.py tests/unit/test_observability.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `git diff --check`
