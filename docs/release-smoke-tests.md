# Release Smoke Tests

This document defines the v1.0 release candidate smoke test matrix.

Release smoke tests are deterministic, credential-free checks that answer one
question before release work proceeds:

```text
Can the core product paths still run together from this checkout?
```

Run them with:

```bash
make release-smoke
```

## Command Contract

`make release-smoke` currently runs:

```bash
make release-eval
docker compose config
uv run pytest tests/unit/test_api_health.py tests/unit/test_cli_commands.py tests/unit/test_worker_cli.py tests/unit/test_tools.py tests/unit/test_kb_search_tool.py tests/integration/test_api_run_lifecycle.py tests/integration/test_runtime_e2e.py tests/integration/test_api_approvals.py tests/integration/test_api_knowledge_base.py tests/integration/test_api_memory.py tests/integration/test_api_evals.py
npm run lint
npm run build
```

The command is intentionally explicit. Avoid replacing it with broad globs
unless the release owner accepts the runtime and failure-triage cost.

## Matrix

| Area | Gate | What It Protects |
| --- | --- | --- |
| Release evals | `make release-eval` | Deterministic RAG and provider-native tool-call behavior gates. |
| Docker config | `docker compose config` | Compose file remains parseable before clean-machine rehearsal. |
| API health | `tests/unit/test_api_health.py` | Basic API app startup and health contract. |
| CLI | `tests/unit/test_cli_commands.py` | Maintainer and user command surfaces still parse and execute. |
| Worker CLI | `tests/unit/test_worker_cli.py` | Worker command modes remain usable and mutually exclusive. |
| Tool execution | `tests/unit/test_tools.py` | Built-in tool contracts and validation behavior. |
| RAG tool | `tests/unit/test_kb_search_tool.py` | Agent-facing retrieval tool behavior. |
| Run lifecycle API | `tests/integration/test_api_run_lifecycle.py` | Agent creation, run creation, queueing, canceling, events, and resume behavior. |
| Runtime worker | `tests/integration/test_runtime_e2e.py` | API-created queued run can be processed by the worker. |
| Approvals API | `tests/integration/test_api_approvals.py` | Approval list, inspect, approve, reject, duplicate, and missing-record behavior. |
| Knowledge base API | `tests/integration/test_api_knowledge_base.py` | KB/document metadata, upload, ingestion, and object store behavior. |
| Memory API | `tests/integration/test_api_memory.py` | Scoped memory write, read, list, and deletion paths. |
| Eval API | `tests/integration/test_api_evals.py` | Persisted eval run API behavior. |
| Web lint | `npm run lint` | Next.js workbench type/lint contract. |
| Web build | `npm run build` | Production Web bundle still compiles. |

## Boundaries

Release smoke tests are not:

- Load tests.
- Soak tests.
- Browser e2e tests.
- Clean-machine rehearsals.
- Live OpenAI provider tests.
- Real pgvector quality tests.
- S3/MinIO interoperability rehearsals.
- Security penetration tests.

Those checks belong to separate release work because they have different
runtime, credential, infrastructure, and flake profiles.

## Failure Handling

If `make release-smoke` fails:

1. Treat the release candidate as blocked.
2. Fix the failing product path or test contract.
3. Re-run `make release-smoke`.
4. Update this matrix if the intended release contract changed.

Do not remove a smoke test only to make release work pass. Demoting a smoke test
requires release-owner approval and a documentation update explaining the new
coverage gap.
