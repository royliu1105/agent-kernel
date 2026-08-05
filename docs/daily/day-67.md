# Day 67: Provider-Native Tool-Call Evals and Regression Tests

## Goal

Add deterministic behavior eval coverage for provider-native tool calls so the
model/tool/model loop can be regression-tested without depending on live LLMs.

## Scope

- Add a provider/tool-call eval runner that reuses the existing eval report
  model.
- Keep the eval runner runtime-agnostic by accepting observed run results from
  a callable.
- Cover successful provider-native safe tool execution.
- Cover approval-required provider-native tools.
- Cover unknown provider-native tool failure.
- Update eval, provider, tool-calling, and lifecycle docs.

## Tasks

- [x] Add provider-native tool-call eval case and observation models.
- [x] Add async eval runner for runtime/tool-call behavior.
- [x] Add assertions for status, errors, event sequence, tool metadata, model
  call count, provider tool loop output, and output content.
- [x] Add runtime-backed regression tests.
- [x] Update Day 67 milestone progress.
- [x] Update eval and provider-native behavior specs.

## Acceptance

- [x] Safe native tool calls pass behavior evals.
- [x] Risky native tool calls pass approval-pause behavior evals.
- [x] Unknown native tools pass safe-failure behavior evals.
- [x] Eval failures produce readable assertion messages.
- [x] Existing RAG eval behavior remains unchanged.

## Verification

- [x] `uv run pytest tests/unit/test_tool_call_evals.py`
- [x] `uv run pytest tests/unit/test_rag_evals.py tests/unit/test_tool_call_evals.py tests/unit/test_runtime_execution.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`

## Notes

- Day 67 does not add persisted eval runs, eval API endpoints, eval Web views,
  LLM-as-judge, or live provider evals.
- Provider-native approval resume remains deferred; Day 67 evaluates the
  approval pause boundary implemented on Day 66.
