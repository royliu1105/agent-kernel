# Feature Spec: LLM Providers

## Goal

Define a stable provider boundary so Agent Kernel can route model calls across mock, OpenAI,
and later third-party or local providers without changing runtime execution semantics.

## Non-Goals

- Streaming responses in Day 4/5.
- Tool/function calling in Day 4/5.
- Provider-specific SDK configuration.
- Multi-provider fallback.
- Prompt database management.

## User Stories

- As a runtime developer, I can call an LLM through a typed interface.
- As a test author, I can run deterministic provider behavior without network access or API keys.
- As a maintainer, I can add a real provider without changing the runtime execution contract.
- As an evaluator, I can rely on stable mock output for regression tests.

## Domain Model

Provider types:

- `LLMMessage`
- `LLMRequest`
- `LLMResponse`
- `LLMUsage`
- `LLMToolDefinition`
- `LLMToolCall`
- `LLMToolChoice`
- `LLMFinishReason`
- `LLMProvider`
- `LLMProviderError`
- `ModelRouter`
- `ModelRoute`
- `UnknownModelRouteError`

Message roles:

```text
system
user
assistant
tool
```

Day 4 response shape:

```json
{
  "provider": "mock",
  "model": "mock-small",
  "text": "Mock response: summarize notes",
  "usage": {
    "input_tokens": 2,
    "output_tokens": 4,
    "estimated_cost": 0.0
  }
}
```

Day 5 routing model:

```text
mock:<model>   -> MockLLMProvider
openai:<model> -> OpenAIProvider
replay:<case>  -> ReplayLLMProvider
```

The prefix is routing metadata. The provider receives the model name without the prefix.

Day 5 OpenAI baseline:

- Uses the OpenAI Responses API shape.
- Reads credentials from `OPENAI_API_KEY`.
- Uses `httpx` behind a small adapter so tests can mock transport.
- Normal tests must not access the network or require an API key.

Day 6 worker routing:

- The worker default router registers `mock` and `openai`.
- Local worker execution should use `mock:*` model references unless the developer explicitly wants
  a real provider smoke test.
- `OpenAIProvider` may be registered without an API key, but it only attempts a real call when a run
  uses an `openai:*` model reference.
- Unknown model routes fail the run clearly and do not leave the run stuck in `running`.

Day 7 replay baseline:

- `ReplayLLMProvider` is an in-memory deterministic provider for regression and future eval
  fixtures.
- Replay lookup matches routed model name, for example `replay:case-001` routes to provider model
  `case-001`.
- The provider returns the pre-recorded `LLMResponse` registered for that model.
- Missing replay cases raise `LLMProviderError` with `error_type = replay_not_found`.
- Replay does not perform network I/O and does not require secrets.
- Prompt-aware matching and fixture file formats are deferred until the eval runner exists.

Day 64 provider-native tool-call contract:

- `LLMToolDefinition` is the provider-facing view of a registered tool:
  - `name`
  - `description`
  - `input_schema`
- `LLMRequest.tools` carries zero or more provider-facing tool definitions.
- `LLMRequest.tool_choice` can express `auto`, `none`, or `required` when a
  provider supports native tool choice.
- `LLMToolCall` is the provider-normalized tool call request shape:
  - `id`
  - `name`
  - `arguments`
  - `raw`
- `LLMResponse.finish_reason` distinguishes normal text completion from
  provider-native tool-call responses.
- `LLMResponse.tool_calls` carries provider-normalized tool call requests.
- `MockLLMProvider` can return deterministic native tool calls for runtime and
  eval tests without network access.
- `OpenAIProvider` serializes supplied tool definitions into Responses API
  function tool payloads.
- Runtime conversion from `ToolMetadata` and `ToolRegistry` to
  `LLMToolDefinition` lives in `kernel_runtime.provider_tools` so provider
  packages do not depend on the tool package.

Day 65 OpenAI native tool-call parsing:

- `OpenAIProvider` parses Responses API `function_call` output items into
  `LLMToolCall`.
- OpenAI `arguments` may be a JSON string or JSON object.
- Malformed function-call arguments raise `LLMProviderError` with
  `error_type = openai_invalid_tool_arguments`.
- Missing function-call ids or names raise `LLMProviderError` with
  `error_type = openai_invalid_tool_call`.
- Responses containing function calls use `finish_reason = tool_calls`.

Day 65 explicitly does not execute provider-native tool calls or run a
model/tool/model loop. That starts in Day 66.

## State Transitions

Provider calls do not own run state. The runtime execution service owns run transitions and uses
provider responses or provider errors to decide whether a run succeeds or fails.

## API / CLI

No provider API or CLI is exposed in Day 4.

Day 5 does not expose provider management through API or CLI. Provider selection is driven by the
run input model string.

## Failure Modes

- Provider raises a typed `LLMProviderError`.
- Provider returns invalid data.
- Runtime constructs an invalid request from run input.
- Model string has no provider prefix.
- Model string references an unregistered provider.
- Replay model references a missing fixture.

Day 4 handles typed provider failures by marking the run as `failed` and storing error details.

Day 5 handles unknown model routes with `UnknownModelRouteError` before making a provider call.

## Security

- Mock provider never performs network I/O.
- Real provider credentials are read from environment variables and must never be committed.
- Provider request metadata should not contain secrets.

## Observability

Provider responses include usage metadata. Runtime persists token counts and cost estimates on the
run record.

## Test Plan

- Mock provider returns deterministic output.
- Mock provider returns stable usage metadata.
- Mock provider can fail deterministically.
- Runtime success path persists final output and usage.
- Runtime failure path persists error type/message.
- Router selects mock and OpenAI providers by prefix.
- OpenAI adapter tests mock transport and do not use network.
- Unknown provider route fails clearly.
- Worker execution through the default router remains deterministic when using `mock:*`.
- Replay provider returns fixture responses by model name.
- Replay provider fails clearly for missing fixture responses.
- Provider contract carries native tool definitions, tool choice, tool calls,
  and finish reason.
- Runtime adapter converts enabled tool metadata into provider-facing tool
  definitions.
- Runtime adapter filters disabled tools.
- OpenAI provider serializes supplied tool definitions without making networked
  tests.
- Mock provider can return deterministic native tool calls.

## Manual Smoke

Optional real-provider smoke testing should be explicit and kept out of normal CI:

```bash
OPENAI_API_KEY=... uv run pytest -m openai_smoke
```
