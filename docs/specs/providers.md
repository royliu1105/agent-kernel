# Feature Spec: LLM Providers

## Goal

Define a stable provider boundary so Agent Kernel can route model calls across mock, OpenAI,
and later third-party or local providers without changing runtime execution semantics.

## Non-Goals

- Streaming responses in Day 4.
- Tool/function calling in Day 4.
- Provider-specific SDK configuration.
- Model routing and fallback.
- Prompt version management.

## User Stories

- As a runtime developer, I can call an LLM through a typed interface.
- As a test author, I can run deterministic provider behavior without network access or API keys.
- As a maintainer, I can add a real provider without changing the runtime execution contract.
- As an evaluator, I can rely on stable mock output for regression tests.

## Domain Model

Day 4 provider types:

- `LLMMessage`
- `LLMRequest`
- `LLMResponse`
- `LLMUsage`
- `LLMProvider`
- `LLMProviderError`

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

## State Transitions

Provider calls do not own run state. The runtime execution service owns run transitions and uses
provider responses or provider errors to decide whether a run succeeds or fails.

## API / CLI

No provider API or CLI is exposed in Day 4.

## Failure Modes

- Provider raises a typed `LLMProviderError`.
- Provider returns invalid data.
- Runtime constructs an invalid request from run input.

Day 4 handles typed provider failures by marking the run as `failed` and storing error details.

## Security

- Mock provider never performs network I/O.
- Real provider credentials are intentionally out of scope for Day 4.
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
