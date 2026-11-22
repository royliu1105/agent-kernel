# Day 05: Model Router and OpenAI Provider Baseline

## Goal

Turn the Day 4 direct provider execution path into a routed provider path with a real-provider
baseline that remains testable without network access.

Day 5 should establish the service path for:

```text
runtime execution -> model router -> selected provider -> mock or OpenAI-compatible provider
```

This is still not the worker loop. The focus is provider selection, OpenAI adapter shape, and
prompt versioning baseline.

## Scope

Day 5 should cover:

- Phase 1 planning alignment.
- Provider spec refinement for routing and OpenAI configuration.
- `ModelRouter` interface/service.
- Provider registry or provider map.
- Routing by model/provider prefix, for example `mock:*` and `openai:*`.
- Typed error for unknown provider/model route.
- OpenAI provider baseline.
- OpenAI request/response conversion tests without real network calls.
- Environment/config surface for `OPENAI_API_KEY`.
- Prompt versioning baseline.
- Lightweight prompt registry, preferably in `kernel-runtime` or a small dedicated module.
- Runtime execution service updated to use router-selected provider.
- Tests for router behavior, OpenAI provider request conversion, prompt registry, and execution
  through the router.

Day 5 should not cover:

- Worker process polling loop.
- Redis-backed queue.
- Streaming.
- Tool/function calling.
- Multi-provider fallback.
- Retry policy.
- Precise token pricing tables.
- Web UI changes.
- Prompt database migrations unless truly needed.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- Should routing live in `kernel-runtime` or `kernel-providers`?
  - Resolved: routing lives in `kernel-runtime`, because it is execution policy. Provider packages
    expose adapters and contracts.
- Should model names use prefixes?
  - Resolved: yes for v0.1: `mock:<model>` and `openai:<model>`. This keeps routing explicit and
    easy to test.
- Should OpenAI SDK be added on Day 5?
  - Resolved: use `httpx` behind a small adapter. This keeps Day 5 lightweight and lets tests mock
    transport behavior without network access.
- Should OpenAI tests call the real API?
  - Resolved: no. Unit tests must not require network or API keys. Real smoke path is
    documented only.
- Where should API keys come from?
  - Resolved: `OPENAI_API_KEY`, never committed config.
- What is the minimal prompt versioning baseline?
  - Resolved: immutable `PromptVersion` model plus an in-memory `PromptRegistry`.
- Should prompt versions be persisted in Postgres on Day 5?
  - Resolved: no. Keep the baseline small; database-backed prompt management can arrive after the
    execution loop is stable.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/providers.md`.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Read `docs/milestones.md` Phase 1 section.
- [x] Refine provider spec with routing and OpenAI baseline decisions.
- [x] Add provider config helpers for OpenAI API key lookup.
- [x] Add OpenAI provider adapter.
- [x] Add tests for OpenAI request/response conversion using mocked client behavior.
- [x] Add model route data types.
- [x] Add `ModelRouter`.
- [x] Add tests for mock route selection.
- [x] Add tests for unknown route failure.
- [x] Add prompt version model.
- [x] Add prompt registry baseline.
- [x] Add prompt registry tests.
- [x] Update runtime execution service to use `ModelRouter`.
- [x] Add execution tests through router.
- [x] Document OpenAI smoke path without running it in CI.
- [x] Update `docs/milestones.md` Phase 1 progress.

## Acceptance

- [x] `ModelRouter` exists and is typed.
- [x] Router can select mock provider from a `mock:*` model string.
- [x] Router can select OpenAI provider from an `openai:*` model string.
- [x] Unknown provider/model route fails clearly.
- [x] OpenAI provider baseline exists.
- [x] OpenAI provider tests do not use network or API keys.
- [x] `OPENAI_API_KEY` config path is documented.
- [x] Prompt version model exists.
- [x] Prompt registry baseline exists.
- [x] Runtime execution can run through router-selected mock provider.
- [x] Tests remain deterministic.
- [x] Phase 1 checklist is updated for completed items.

## Verification

Run the available checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
docker compose ps
docker compose config
pre-commit run --all-files
```

Optional manual OpenAI smoke path should be documentation-only unless explicitly requested:

```bash
OPENAI_API_KEY=... uv run pytest -m openai_smoke
```

## Notes

- Keep Day 5 centered on routing and adapter boundaries.
- Do not require a real OpenAI API key for normal tests.
- Keep prompt versioning intentionally small but immutable.
- Avoid provider fallback and retry until the first worker execution path is working.
- Prefer explicit model prefixes over clever inference.

## Completion Notes

- Implemented explicit `ModelRouter` with `mock:*` and `openai:*` style model references.
- Added `UnknownModelRouteError` and `ModelRoute`.
- Added OpenAI Responses API baseline adapter using `httpx`.
- Added OpenAI API key config helper through `OPENAI_API_KEY`.
- Added immutable `PromptVersion` and in-memory `PromptRegistry`.
- Updated `RunExecutionService` to execute through router-selected providers.
- Added provider, router, OpenAI adapter, prompt registry, and routed execution tests.
- Added `docs/specs/prompts.md`.
- Updated provider and run lifecycle specs with Day 5 routing semantics.
- Verification passed:
  - `uv sync`
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `docker compose ps`
  - `docker compose config`
  - `pre-commit run --all-files`

Known caveat:

- OpenAI provider is implemented and unit-tested with mocked transport, but no real API smoke test
  was run. Real smoke remains explicit and opt-in.

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 5：请按照 docs/daily/day-05.md 执行今天的计划。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-05.md、docs/specs/providers.md、docs/specs/run-lifecycle.md 和 docs/milestones.md。
- 只实现 Day 5 scope 内的内容，不提前做 worker loop、tool calling、streaming、fallback 或 Web UI。
- OpenAI provider 测试不能真实访问网络，也不能要求 API key。
- 如果 provider routing 或 prompt 语义变化，更新相关 spec。
- 完成后运行 Day 5 verification commands。
- 更新 docs/daily/day-05.md 的 checklist。
- 如 phase-level progress 变化，更新 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
