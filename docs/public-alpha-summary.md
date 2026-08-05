# Public Alpha Summary: Day 39-51

## Status

Public Alpha is complete as an early-user hardening milestone:

```text
Day 39-51: Public Alpha hardening
```

Public Alpha turned the published `v0.1.0` runtime foundation into a project
that early external users can clone, run, inspect, and critique with a clearer
first-run path, better examples, stronger feedback loops, and live Web
Workbench integration for the highest-value backend-supported workflows.

## Completion Statement

Public Alpha is complete under this scope:

```text
Make Agent Kernel usable and understandable for early external users without
expanding the project into a hosted SaaS, full production multi-tenant system,
or complete v1.0 hardening release.
```

The milestone does not mean every planned v1.0 capability is done. It means the
published foundation is ready for early external feedback.

## What Users Can Do Now

Early users can:

- Follow the README and Quickstart to run the local runtime.
- Use SQLite and mock models without external LLM credentials.
- Create and execute mock agent runs.
- Run the worker and inspect run state.
- Exercise tools, approvals, retry/fallback, RAG, memory, and eval workflows.
- Start the API and Web Workbench.
- Use live Web Workbench paths for health, run lookup, timeline, approvals,
  approval approve/reject, knowledge base list, and retrieval search.
- Run the Public Alpha walkthrough and HTTP request examples.
- Use issue templates to report bugs, feature requests, or Public Alpha
  feedback.

## Completed Public Alpha Work

- Public Alpha guide.
- Public feedback channels and issue templates.
- README first-run path updates.
- Quickstart first-user polish.
- Troubleshooting guide expansion.
- Public Alpha walkthrough.
- Public Alpha HTTP request collection.
- Example refresh for mock run, approvals, RAG, memory, and evals.
- Live Web health integration.
- Live Web run lookup.
- Live Web run event timeline.
- Live Web approval inbox.
- Live Web approval approve/reject mutation UI.
- Live Web knowledge base list.
- Live Web retrieval search with raw cited chunks.
- Workbench scope banner that distinguishes live API paths from preview data.
- Expanded RAG behavior eval coverage.
- Improved CLI/API-unreachable error guidance.
- Public Alpha release notes and maintainer announcement draft.
- Milestone tracking updates for Day 39-51.

## Live Workbench Scope

The Public Alpha live Web goal is complete for the backend-supported key paths.

Live API-backed paths:

- Health status through `/api/agent-kernel/health`.
- Run detail through `/api/agent-kernel/runs/{run_id}`.
- Run timeline through `/api/agent-kernel/runs/{run_id}/events`.
- Approval inbox through `/api/agent-kernel/approvals`.
- Approval approve/reject through same-origin approval mutation proxy routes.
- Knowledge base list through `/api/agent-kernel/knowledge-bases`.
- Retrieval search through
  `/api/agent-kernel/knowledge-bases/{knowledge_base_id}/retrieve`.

Preview-backed areas that intentionally remain:

- Dashboard summary cards.
- Agent catalog-style views.
- Some local approval preview examples.
- Document ingestion preview surfaces.
- Memory preview surfaces.
- Eval report preview surfaces.

These remaining preview-backed areas are not Public Alpha blockers because the
backend does not yet expose all list, summary, persisted eval, and operator
aggregation endpoints needed for a fully live Workbench.

## Verification

Day 51 local verification should cover:

```bash
docker compose config
uv run ruff check .
uv run mypy .
uv run pytest
uv run agent-kernel eval report evals/rag-smoke.json
npm run lint
npm run build
npm run test:e2e
git diff --check
```

GitHub CI should be checked after the closure commit is pushed.

## Known Remaining Limitations

Public Alpha intentionally does not include:

- Auth, RBAC, workspace scope, browser sessions, or tenant isolation.
- Provider-native function calling.
- Provider-returned persisted tool-call loop.
- Durable execution with Redis queue, leases, heartbeats, and replay recovery.
- Production-grade human approval authorization and policy engine.
- Real embedding providers.
- pgvector-native indexes.
- S3/MinIO object storage backend.
- Hybrid search, BM25, RRF, reranking, or query rewriting.
- OpenTelemetry exporters and Prometheus endpoint.
- Persisted eval API and live eval Workbench views.
- Upgrade, backup, restore, and full production security documentation.

These items move into Beta and v1.0 hardening.

## Beta Entry Point

Beta starts on Day 52 and should focus on production hardening:

- Auth, RBAC, and workspace scope.
- Durable execution.
- Provider-native function calling and persisted tool calls.
- Production storage backends.
- Real embeddings and pgvector.
- Object storage through S3/MinIO.
- OpenTelemetry and Prometheus integration.
- Persisted evals.
- More live Workbench operator views.
- Upgrade, backup, restore, and security hardening docs.

Canonical plan: [Post-v0.1 Completion Plan](post-v0.1-plan.md).
