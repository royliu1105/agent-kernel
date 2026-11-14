# Release Eval Gates

This document defines the v1.0 release candidate eval gates.

Release eval gates are deterministic, credential-free checks that must pass
before release readiness can be claimed. They complement unit tests, integration
tests, Web smoke tests, migration smoke tests, and clean-machine rehearsals.

## Blocking Gates

Run all blocking eval gates with:

```bash
make test-db-up
make release-eval
```

Database-backed gates require isolated PostgreSQL. Make supplies its test URL;
for direct commands below set `AGENT_KERNEL_TEST_POSTGRES_URL` as described in
[PostgreSQL-only testing](postgresql-only.md). No provider credentials are needed.

The command currently runs:

```bash
uv run agent-kernel eval report evals/rag-smoke.json
uv run agent-kernel eval report evals/release-rag-gate.json
uv run pytest tests/unit/test_tool_call_evals.py
uv run pytest -q tests/integration/test_bounded_native_execution.py tests/integration/test_runtime_backoff.py tests/integration/test_native_continuation_wire.py tests/integration/test_execution_budget_edges.py
uv run python scripts/timeline_regression.py
```

CI runs the same command in the Python job.
The separate Python `Test` step also runs the actual-adapter HTTP contracts and
golden mutation tests below. They are not optional live tests, and a successful
`make release-eval` alone does not establish that those additional tests passed.

## RAG Release Gate

Datasets:

```text
evals/rag-smoke.json
evals/release-rag-gate.json
```

Purpose:

- Preserve the existing cheap retrieval smoke gate.
- Catch retrieval regressions that affect result count.
- Catch top-result relevance regressions.
- Catch missing citation regressions.
- Catch citation source URI regressions.
- Catch empty knowledge base behavior regressions.
- Catch expected missing knowledge base error behavior.

Current cases:

| Case | What It Protects |
| --- | --- |
| `deployment-runbook-citation` | Top result contains deployment rollback terms and cited source. |
| `backup-restore-citation` | Multi-result retrieval still returns cited backup/restore content. |
| `empty-knowledge-base-safe` | Empty retrieval paths return no results cleanly. |
| `missing-knowledge-base-safe-error` | Missing knowledge base errors are deterministic and expected. |

The RAG gate runs through:

```bash
agent-kernel eval report evals/rag-smoke.json
agent-kernel eval report evals/release-rag-gate.json
```

It uses the deterministic cheap retrieval path in the CLI by default, so it
does not require OpenAI credentials, pgvector, Postgres, or uploaded documents.

## Provider-Native Tool-Call Gate

Command:

```bash
uv run pytest tests/unit/test_tool_call_evals.py
```

Purpose:

- Catch provider-native tool-call parsing regressions.
- Catch safe native tool execution regressions.
- Catch approval-required native tool pause regressions.
- Catch unknown native tool failure regressions.
- Catch model/tool/model loop regressions.
- Catch provider tool-call id persistence regressions.

Current behavior cases:

| Case | What It Protects |
| --- | --- |
| `safe-native-tool` | Native provider tool calls can complete a model/tool/model loop. |
| `approval-native-tool` | Risky native tool calls pause at `waiting_approval`. |
| `unknown-native-tool` | Unknown native tools fail safely before a follow-up model call. |

This gate is runtime-backed but deterministic. It uses mock providers, local
isolated PostgreSQL test storage, and built-in tools. Start `make test-db-up`
before running database-backed gates; see [test isolation](postgresql-only.md).

## Runtime Timeline Gate

```bash
uv run python scripts/timeline_regression.py
uv run pytest tests/integration/test_timeline_regression.py
```

The CLI command is part of `make release-eval`; its mutation tests run in the
Python test suite. Seven scenarios cover native tools, approved/rejected
approval, model retry/fallback, tool retry and lease recovery. Event ordering,
persisted state and execution counts are checked against reviewed goldens.
Fixture providers also validate incoming messages and tool-result contents,
including correlation to the persisted tool-call UUID. Removing or corrupting
the follow-up result must fail the gate, not still return a canned success.
See [behavior regression](behavior-regression.md) for the exact scope and limits.

## Actual Provider Wire Contracts

```bash
uv run pytest tests/unit/test_openai_provider.py tests/integration/test_openai_runtime_contract.py
```

These are blocking tests in the existing Python CI `Test` step. They use the
actual OpenAI adapter, HTTP mock transport and actual runtime/repositories,
without credentials, sockets or paid requests. They cover:

- Responses `function_call` history and matching `function_call_output` with
  provider call IDs, arguments, the actual persisted result and final answer.
- Provider-native reasoning/message/call items retained in order through runtime
  metadata, with encrypted content preserved and no reasoning in answer text.
- Rejecting missing, orphaned or duplicate tool history before HTTP dispatch.
- Bounded retry/fallback for temporary 429/503, read timeout and connection
  failure; exact attempt counts and persisted retry/fallback events.
- No retry/fallback for malformed requests, authorization failure or known
  billing/quota exhaustion, and no hidden adapter retries.
- Transient failure after tool success retries synthesis only, bounded by the
  configured policy, with identical wire history and no tool replay. Exact
  attempt events, usage ledger rows/totals and permanent/exhausted failures are
  verified; native follow-up never falls back to another model/provider.

These contracts do not certify backoff or `Retry-After` scheduling, arbitrary
provider built-in tool outputs, multi-call loops, or model continuation after approval.
Those runtime limitations are listed in
[the R3 scope](behavior-regression.md#openai-wire-contracts-r3). Real network
availability and live model behavior remain separate optional evidence.

## Non-Blocking Optional Evals

These are valuable but not default release blockers yet:

- Live OpenAI provider evals.
- LLM-as-judge evals.
- Real pgvector retrieval quality evals.
- Long-running regression suites.
- Cost and latency trend comparisons.
- Human review of generated answers.

They remain optional because they need credential, cost, latency, and flake
policy decisions before becoming default CI gates.

## Adding a Blocking Eval

Before adding a new blocking eval:

1. Make it deterministic.
2. Avoid external network access by default.
3. Avoid paid provider calls by default.
4. Keep runtime short enough for CI.
5. Include readable failure messages.
6. Add it to `make release-eval`.
7. Add it to this document.
8. Add or update tests that prove the gate can run from a clean checkout.

Do not add secret-bearing or credential-dependent evals to default release gates.

## Release Requirements

Before v1.0 final:

- `make release-eval` must pass locally.
- GitHub CI `Release Eval Gates` must pass.
- GitHub CI `Test` must pass, including provider wire and timeline mutation tests.
- Release notes must list any eval gate changes.
- Known eval blind spots must be listed in release limitations.

If a release gate fails, either fix the regression or explicitly remove/demote
the gate with release-owner approval and documentation updates.
