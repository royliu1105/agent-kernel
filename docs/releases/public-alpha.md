# Agent Kernel Public Alpha Release Notes

Status:

```text
Draft for Public Alpha closure
```

Agent Kernel Public Alpha is the early-user hardening release track after the
published `v0.1.0` foundation.

The purpose of Public Alpha is to make Agent Kernel easier for external
developers to clone, run, inspect, and critique before the Beta production
hardening track begins.

## Positioning

Agent Kernel is a self-hosted, observable, evaluable, resumable AI Agent runtime
for building agent applications with tools, knowledge bases, memory, human
approval, and operator workflows.

Public Alpha is best understood as:

```text
v0.1.0 runtime foundation + early-user usability hardening
```

It is not a hosted SaaS, no-code builder, agent marketplace, or v1.0 production
commitment.

## Who Should Try It

Public Alpha is intended for:

- Developers learning production-grade AI Agent architecture.
- Engineers evaluating an agent runtime foundation for internal prototypes.
- Open-source contributors interested in runtime, RAG, memory, eval, Web
  Workbench, or deployment hardening.
- Teams that want to study agent execution, approval, retrieval, memory, and
  eval workflows in a self-hosted codebase.

It is not yet intended for:

- Public multi-tenant production workloads.
- Untrusted arbitrary user tool execution.
- Long-running durable production workflows.
- Fully managed hosted-agent use cases.

## What Is Included

Public Alpha includes the `v0.1.0` foundation:

- Core agent run lifecycle.
- FastAPI API.
- Typer CLI.
- Background worker.
- LLM provider abstraction and model routing.
- Mock, replay, and OpenAI provider baseline.
- Prompt versioning foundation.
- Tool interface, registry, schema validation, and executor.
- Tool risk levels, policy decisions, and approval records.
- Approval interrupt and resume.
- Retry and fallback policy.
- Knowledge base, document upload, ingestion, chunking, indexing, retrieval,
  citations, and `kb_search` tool.
- Scoped memory CRUD, retrieval, and model context injection.
- Trace IDs, structured logs, runtime metrics, and retrieval metrics.
- Deterministic behavior evals and cheap eval CI path.
- Next.js Agent Workbench.
- Docker Compose local stack definition.
- Release-facing docs, examples, and contribution guides.

Public Alpha hardening adds:

- GitHub issue templates and a documented feedback path.
- First-run README and Quickstart polish.
- Public Alpha walkthrough and HTTP request examples.
- Improved examples for mock runs, approvals, RAG, memory, and evals.
- Live Web Workbench health integration.
- Live run detail and timeline lookup.
- Live approval inbox integration.
- Live approval approve/reject mutation UI.
- Live knowledge base list integration.
- Live retrieval search integration.
- Clear Workbench scope banner for live API paths versus preview data.
- Expanded RAG behavior eval coverage.
- More actionable CLI and API-unreachable error guidance.
- Troubleshooting coverage for common setup, Docker, Web, and CLI issues.

## What To Try First

Recommended path:

1. Follow the [Quickstart](../quickstart.md).
2. Run the [Public Alpha Walkthrough](../../examples/public-alpha-walkthrough.md).
3. Start the API and Web Workbench.
4. Open the Workbench and confirm live API health.
5. Look up a run by ID and inspect timeline events.
6. Try approval inbox and approval mutation flows.
7. Create a knowledge base, ingest content, and run retrieval search.
8. Run the deterministic RAG eval report.
9. Start the Docker Compose stack when Docker Desktop is available.

The default path uses mock models and SQLite. External LLM credentials are not
required unless users choose an `openai:*` model.

## Workbench Scope

The Workbench is becoming a real operator console, but Public Alpha is still a
mixed state:

- Live API-backed: health, run lookup, run timeline, approval inbox, approval
  approve/reject actions, knowledge base list, retrieval search.
- Preview-backed: some dashboard summaries, agent catalog views, document
  ingestion previews, memory preview surfaces, and eval report previews.

This is intentional for Public Alpha. The goal is to harden the highest-value
operator paths without pretending every view is fully live.

## Known Limitations

Important limitations:

- Auth, RBAC, browser sessions, workspace scope, and tenant isolation are not
  implemented.
- Provider-native function calling is not implemented.
- Automatic model-driven tool-choice planning is not implemented.
- Provider-returned tool calls are not persisted as a durable loop.
- Redis-backed distributed queue, worker leases, heartbeats, and durable
  execution guarantees are not implemented.
- Human approvals exist, but production-grade approval policies and workspace
  authorization are not complete.
- OpenAI embeddings and other real embedding providers are not implemented.
- pgvector-native vector indexes are not implemented.
- S3/MinIO object storage backend is not implemented.
- Retrieval is not yet hybrid search; BM25, RRF, reranking, and query rewriting
  are future work.
- OpenTelemetry exporters and Prometheus endpoint are not implemented.
- Eval runs are not persisted and eval API endpoints are not implemented.
- Web Workbench still contains preview-backed areas.
- Upgrade, backup, restore, and production security hardening docs are not final.

These items are intentionally reserved for Beta and v1.0 hardening so Public
Alpha can stay focused on first-user experience and feedback quality.

## Feedback Requested

Please file GitHub Issues for:

- Setup failures or confusing first-run steps.
- Missing or unclear examples.
- API, CLI, worker, Web, or Docker errors.
- Workbench areas where live versus preview data is unclear.
- RAG, memory, approval, retry, or eval behavior that is surprising.
- Documentation gaps.
- Production-hardening priorities that would affect real adoption.

Good reports include:

- Exact command or UI action.
- Expected result.
- Actual result.
- Operating system and tool versions.
- Release or commit SHA.
- Redacted logs or screenshots.

Do not include API keys, tokens, secrets, private documents, or private logs.

## Maintainer Announcement Draft

Short announcement:

```text
Agent Kernel is now in Public Alpha hardening after the v0.1.0 foundation
release.

It is a self-hosted AI Agent runtime with API, CLI, worker, tools, approvals,
RAG, memory, observability, deterministic evals, Docker Compose, and a Next.js
Workbench.

Public Alpha focuses on first-run reliability, examples, feedback loops, live
Workbench integration, and clear limitations before Beta production hardening.
Early feedback is especially useful around setup, docs, examples, Workbench
clarity, RAG/memory behavior, eval coverage, and production-hardening
priorities.
```

Useful links:

- [README](../../README.md)
- [Quickstart](../quickstart.md)
- [Public Alpha Guide](../public-alpha.md)
- [Public Alpha Walkthrough](../../examples/public-alpha-walkthrough.md)
- [v0.1.0 Release Notes](v0.1.0.md)
- [Post-v0.1 Completion Plan](../post-v0.1-plan.md)
