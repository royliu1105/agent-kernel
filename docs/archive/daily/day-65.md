# Day 65: OpenAI Native Tool-Call Parsing and Persistence

## Goal

Parse OpenAI Responses API native function-call output into Agent Kernel's
provider-normalized `LLMToolCall` contract and persist those tool-call requests
with provider metadata for later execution.

## Scope

- Parse OpenAI `function_call` output items into `LLMToolCall`.
- Reject malformed provider function-call arguments with typed provider errors.
- Add durable provider metadata fields to `tool_calls`.
- Add a migration for provider-native tool-call metadata.
- Add repository support for provider-originated requested tool calls.
- Add runtime helper to persist provider-native tool calls without executing
  them.
- Update provider, tool-calling, run lifecycle, and milestone docs.

## Tasks

- [x] Parse OpenAI native function-call output.
- [x] Map OpenAI tool-call responses to `finish_reason = tool_calls`.
- [x] Reject malformed OpenAI function-call argument JSON.
- [x] Add provider metadata fields to `ToolCall` domain and storage records.
- [x] Add migration for provider-native tool-call metadata.
- [x] Add repository method for provider-originated requested tool calls.
- [x] Add runtime persistence helper for normalized provider tool calls.
- [x] Update daily plan and milestone progress.
- [x] Update provider, tool-calling, and run lifecycle specs.

## Acceptance

- [x] OpenAI function-call output with JSON string arguments becomes a
  normalized `LLMToolCall`.
- [x] OpenAI malformed function-call arguments fail with
  `openai_invalid_tool_arguments`.
- [x] Provider-originated tool calls persist provider name, provider tool-call
  id, raw provider payload, normalized name, and normalized arguments.
- [x] Runtime persistence helper derives risk level from registered tools.
- [x] Unknown provider-requested tools are persisted with `dangerous` risk so
  Day 66 can fail or gate them conservatively.

## Verification

- [x] `uv run pytest tests/unit/test_openai_provider.py tests/unit/test_tool_call_repository.py tests/unit/test_provider_tools.py tests/unit/test_migrations.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_openai_provider.py tests/unit/test_tool_call_repository.py tests/unit/test_provider_tools.py tests/unit/test_migrations.py`
- [x] `uv run pytest`

## Notes

- Day 65 does not execute provider-native tool calls.
- Day 65 does not feed tool results back into a second model call.
- Day 65 does not change explicit `input.tool` execution behavior.
- Day 65 intentionally stores provider metadata as first-class fields instead
  of hiding provider ids or raw payloads inside tool arguments.
