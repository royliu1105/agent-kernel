# Agent Kernel Roadmap

This roadmap separates the published v0.1.0 foundation from Public Alpha, Beta,
and v1.0 completion work.

See [Post-v0.1 Completion Plan](docs/post-v0.1-plan.md) for the canonical
post-v0.1 execution plan.

## v0.1.0 Release

Goal:

```text
A developer can clone the repository, run the runtime locally, inspect behavior,
run evals, open the Workbench, and understand known limitations.
```

Status:

```text
Published
```

Completed foundations:

- Core run lifecycle.
- LLM provider abstraction and routing.
- Mock, replay, and OpenAI provider baseline.
- Prompt versioning.
- Tool interface and safe execution.
- Policy decisions.
- Human approval interrupt/resume.
- Retry and fallback.
- RAG ingestion, chunking, indexing, retrieval, and `kb_search`.
- Scoped memory.
- Trace IDs, structured logs, metrics, and cheap evals.
- Web Workbench foundation.
- Playwright smoke tests.
- Local Docker Compose stack definition.

Completed release hardening:

- Full Compose startup verification from a clean checkout.
- Production config review.
- Final docs pass.
- Release checklist.
- v0.1.0 release notes.
- Dependency audit review.
- GitHub CI verification.
- Annotated `v0.1.0` tag.
- GitHub Release.

## Public Alpha

Goal:

```text
An early external user can try Agent Kernel, understand the project, report
issues, and give useful feedback without maintainer hand-holding.
```

Planned improvements:

- Public feedback channels and issue templates.
- README and quickstart polish for first external users.
- Better quickstart troubleshooting.
- Better examples.
- More Web polish and live API integration for core workflows.
- More behavior eval coverage.
- Better error messages.
- Docker Compose startup hardening.
- First external-user feedback loop.
- Public Alpha announcement.

## Beta

Goal:

```text
Agent Kernel is credible for internal production pilots and serious extension
by other developers.
```

Planned improvements:

- Authentication baseline.
- Authorization/RBAC baseline.
- Tenant or workspace scoping model.
- Provider-native function calling.
- Durable model/tool/model execution loop.
- Persisted tool-call records.
- Redis-backed durable queue.
- Worker leasing and stuck-run recovery.
- OpenTelemetry exporters.
- Prometheus-compatible metrics endpoint.
- S3/MinIO object storage backend.
- OpenAI embeddings backend.
- pgvector-native vector store.
- Persisted eval runs and eval API.
- Live Web Workbench integration for core operator workflows.

## v1.0

Goal:

```text
Stable self-hosted production-grade open-source AI Agent runtime.
```

v1.0 must include:

- Stable public API and CLI compatibility contract.
- Durable execution across worker restarts.
- Durable tool-call and approval records.
- Production-grade auth and permission boundaries.
- Configurable storage backends for database, object storage, and vector search.
- Provider-native tool calling.
- Real embeddings path.
- Live Web Workbench for core operations.
- OpenTelemetry and Prometheus-compatible observability.
- Persisted eval runs and release-blocking regression gates.
- Security, deployment, backup, and upgrade documentation.

## Later Production Hardening

Potential future work:

- Hybrid retrieval with BM25.
- RRF and reranking.
- Query rewriting.
- Semantic memory retrieval.
- Automatic memory writes and consolidation.
- Secrets manager integration.
- Remote sandbox execution.
- Visual regression testing.
- Accessibility automation.
- Cross-browser Playwright matrix.
- Plugin or extension authoring guide.
- Public hosted SaaS.
- Enterprise SSO.
- Multi-region deployment.

## Non-Goals for v0.1

v0.1 intentionally does not try to be:

- A public multi-tenant SaaS.
- A fully managed cloud platform.
- A general no-code agent builder.
- A chat-only demo.
- A replacement for production identity, secrets, and network controls.
