# Day 66: Model/Tool/Model Execution Loop

## Goal

Connect provider-native tool-call responses into the runtime execution loop so
one safe model-requested tool can be persisted, policy-checked, executed, and
fed back into a second model call before the run completes.

## Scope

- Send registered tool definitions to model providers during model execution.
- Detect provider-native tool-call responses.
- Persist exactly one provider-native tool call through the Day 65 persistence
  path.
- Reuse the existing policy, approval, tool execution, retry, persistence,
  metrics, and timeline paths.
- Add a follow-up model request containing the tool result.
- Complete the run from the second model response.
- Add tests for safe completion, approval pause, and unknown tool failure.

## Tasks

- [x] Attach provider tool definitions to model requests.
- [x] Add single-tool provider-native execution branch.
- [x] Persist provider-native requested tool calls before execution.
- [x] Reuse policy checks for native tool calls.
- [x] Execute allowed native tool calls through the existing tool executor.
- [x] Send tool result back to the provider as a follow-up tool message.
- [x] Complete the run from the follow-up model response.
- [x] Add native tool loop regression tests.
- [x] Update daily plan and milestone progress.
- [x] Update provider, tool-calling, and run lifecycle specs.

## Acceptance

- [x] A provider-native safe tool call can complete a model/tool/model run.
- [x] The tool call is durable and includes provider metadata.
- [x] The follow-up provider request contains the executed tool result.
- [x] Usage totals include both model calls in the loop.
- [x] Risky provider-native tools pause for approval instead of executing.
- [x] Unknown provider-native tools fail safely and do not trigger a second
  model call.
- [x] Existing explicit `input.tool` behavior remains unchanged.

## Verification

- [x] `uv run pytest tests/unit/test_runtime_execution.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`
- [x] `uv run pytest`

## Notes

- Day 66 supports exactly one provider-native tool call per loop.
- Day 66 does not implement multi-tool fanout, nested tool loops, planner
  recursion, or streaming tool calls.
- Day 66 pauses risky native tools for approval but does not yet resume them
  into a second model call after approval. That remains a later hardening item.
- Day 66 does not add provider-native behavior evals; those are Day 67.
