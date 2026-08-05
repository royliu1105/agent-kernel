# Day 64: Provider-Native Tool-Call Adapter Contract

## Goal

Start the provider-native tool-calling track by defining the typed contract that
lets model providers receive tool schemas and return tool-call requests without
leaking provider-specific response shapes into the runtime.

## Scope

- Add provider-facing tool definition, tool-call, tool-choice, and finish-reason
  models.
- Add a runtime adapter from internal `ToolMetadata` / `ToolRegistry` to provider
  tool definitions.
- Teach the OpenAI provider request serializer to include provider-native tool
  definitions when they are supplied.
- Add deterministic mock-provider support for returning native tool calls in
  tests.
- Update provider and tool-calling specs.

## Tasks

- [x] Add provider-native tool contract models.
- [x] Export the new provider contract types.
- [x] Add runtime tool metadata to provider tool definition adapter.
- [x] Add OpenAI request payload serialization for tool definitions.
- [x] Add provider/tool adapter regression tests.
- [x] Update daily plan and milestone progress.
- [x] Update provider and tool-calling specs.

## Acceptance

- [x] `LLMRequest` can carry provider-facing tool definitions and tool-choice
  preference.
- [x] `LLMResponse` can carry provider-native tool calls and finish reason.
- [x] Runtime can convert enabled registered tools to provider tool definitions.
- [x] Disabled tools are not exposed through the registry adapter.
- [x] OpenAI request payloads include function tool definitions when tools are
  supplied.
- [x] Mock provider can return deterministic tool calls for future runtime tests.

## Verification

- [x] `uv run pytest tests/unit/test_mock_provider.py tests/unit/test_openai_provider.py tests/unit/test_provider_tools.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_mock_provider.py tests/unit/test_openai_provider.py tests/unit/test_provider_tools.py`
- [x] `uv run pytest`

## Notes

- Day 64 does not parse provider-returned OpenAI function calls from raw
  Responses API output. That starts on Day 65.
- Day 64 does not persist provider-native tool calls. That starts on Day 65.
- Day 64 does not add the model/tool/model execution loop. That is Day 66.
- Day 64 does not change explicit `input.tool` behavior.
