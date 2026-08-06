# Release Eval Gates

This document defines the v1.0 release candidate eval gates.

Release eval gates are deterministic, credential-free checks that must pass
before release readiness can be claimed. They complement unit tests, integration
tests, Web smoke tests, migration smoke tests, and clean-machine rehearsals.

## Blocking Gates

Run all blocking eval gates with:

```bash
make release-eval
```

The command currently runs:

```bash
uv run agent-kernel eval report evals/rag-smoke.json
uv run agent-kernel eval report evals/release-rag-gate.json
uv run pytest tests/unit/test_tool_call_evals.py
```

CI runs the same command in the Python job.

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
SQLite-backed test storage, and built-in tools.

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
- Release notes must list any eval gate changes.
- Known eval blind spots must be listed in release limitations.

If a release gate fails, either fix the regression or explicitly remove/demote
the gate with release-owner approval and documentation updates.
