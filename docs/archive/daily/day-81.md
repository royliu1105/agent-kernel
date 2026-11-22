# Day 81: Release-Blocking Eval Suite Definition

Goal:

Define the v1.0 release candidate eval gates that must pass before release
readiness can be claimed.

Scope:

- Add a release RAG eval dataset.
- Add a maintainer-facing release eval command.
- Wire release eval gates into CI explicitly.
- Document release-blocking eval expectations and boundaries.
- Update eval specs, docs index, daily index, and milestone tracking.
- Do not add LLM-as-judge or live-provider evals to default CI.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing deterministic RAG and provider-native tool-call evals.
- [x] Add release RAG eval dataset.
- [x] Add `make release-eval`.
- [x] Add explicit CI release eval gate.
- [x] Add release eval gate documentation.
- [x] Update eval spec with Day 81 release gate scope.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Release-blocking RAG evals can run through CLI.
- [x] Provider-native tool-call evals are part of the release gate command.
- [x] Default release gates remain deterministic and credential-free.
- [x] CI runs the release eval gate explicitly.
- [x] Real-model and LLM-as-judge evals remain optional/non-blocking.
- [x] Day 81 does not introduce network-dependent default evals.

Verification:

- [x] `uv run agent-kernel eval report evals/release-rag-gate.json`
- [x] `uv run pytest tests/unit/test_rag_evals.py tests/unit/test_tool_call_evals.py`
- [x] `make release-eval`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- The release gate intentionally uses deterministic mock/cheap eval paths. Live
  provider evals can be added later as optional confidence checks, but they must
  not block default CI without credential and cost policy decisions.
