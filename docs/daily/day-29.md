# Day 29: Phase 4 Closure and Cheap Eval CI

## Goal

Close Phase 4 by making deterministic eval reports runnable from the CLI and CI,
then document completed observability/eval capabilities and deferred scope.

Day 29 should establish this closure baseline:

```text
JSON eval dataset -> CLI eval report -> CI cheap eval -> Phase 4 summary
```

## Scope

Day 29 should cover:

- Eval report serialization.
- Local deterministic RAG eval report command.
- Cheap eval fixture dataset.
- Makefile cheap eval target.
- CI cheap eval step.
- Tests for eval report output and CLI behavior.
- Phase 4 summary document.
- Milestone reconciliation.
- Documentation index updates.
- Full verification.

Day 29 should not cover:

- Full eval API.
- Persisted eval runs.
- LLM-as-judge.
- Real model evals in default CI.
- Full agent behavior eval platform.
- OpenTelemetry exporter setup.
- Full RunStep persistence.
- Web UI eval reports.

## Tasks

- [x] Check current git status.
- [x] Read Phase 4 milestones, eval spec, existing CLI, Makefile, and CI.
- [x] Create Day 29 daily plan.
- [x] Add eval report serialization.
- [x] Add local CLI eval report command.
- [x] Add cheap eval fixture dataset.
- [x] Add Makefile cheap eval target.
- [x] Add CI cheap eval step.
- [x] Add tests for report serialization and CLI output.
- [x] Add Phase 4 summary document.
- [x] Update specs, milestones, docs index, and daily index.
- [x] Run focused tests.
- [x] Run full verification.

## Acceptance

- [x] A JSON RAG eval dataset can be run through CLI.
- [x] CLI eval report prints pass/fail counts and assertion details as JSON.
- [x] CLI exits non-zero for failing reports by default.
- [x] CI runs a deterministic cheap eval.
- [x] Phase 4 summary documents completed capabilities and deferred scope.
- [x] Day 29 does not add persisted eval runs, LLM-as-judge, OTel exporters, or UI reports.

## Verification

Run:

```bash
uv run pytest tests/unit/test_rag_evals.py tests/unit/test_cli_commands.py
uv run agent-kernel eval report evals/rag-smoke.json
uv run ruff check .
uv run mypy .
uv run pytest
git diff --check
```

## Notes

- Keep CI eval deterministic and cheap.
- Keep real-model evals optional and outside default CI.
- Treat OpenTelemetry exporter setup and full RunStep persistence as Phase 4 deferred scope.

## Completion Notes

- Added stable eval report serialization.
- Added local CLI eval report command.
- Added deterministic cheap RAG eval fixture.
- Added Makefile `cheap-eval` target.
- Added GitHub Actions cheap eval step.
- Added tests for eval report serialization and CLI success/failure behavior.
- Added Phase 4 summary document.
- Updated eval spec, milestones, docs index, and daily index.
- Kept persisted eval runs, LLM-as-judge, full eval API, OpenTelemetry exporters,
  full RunStep persistence, and UI eval reports deferred.

Verification passed:

- `uv run pytest tests/unit/test_rag_evals.py tests/unit/test_cli_commands.py`
- `uv run agent-kernel eval report evals/rag-smoke.json`
- `uv run ruff check .`
- `uv run mypy .`
- `uv run pytest`
- `git diff --check`
