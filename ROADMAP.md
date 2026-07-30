# Agent Kernel Roadmap

This roadmap separates the current v0.1 release target from Public Alpha and
later production hardening work.

## v0.1 Release

Goal:

```text
A developer can clone the repository, run the runtime locally, inspect behavior,
run evals, open the Workbench, and understand known limitations.
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

Remaining v0.1 release work:

- Full Compose startup verification from a clean checkout.
- Production config review.
- Final docs pass.
- Release checklist.
- v0.1.0 release notes.
- Dependency audit review.

## Public Alpha

Goal:

```text
An early external user can try Agent Kernel, understand the project, report
issues, and give useful feedback without maintainer hand-holding.
```

Planned improvements:

- Better quickstart troubleshooting.
- Better examples.
- More Web polish.
- More behavior eval coverage.
- Better error messages.
- Docker Compose startup hardening.
- First external-user feedback loop.
- Public Alpha announcement.

## Later Production Hardening

Potential future work:

- Live Web API integration for all Workbench views.
- Authentication and authorization.
- Tenant isolation.
- Provider-native function calling.
- Automatic agent planning for tool choice.
- Durable model/tool/model execution loop.
- Async task queue backed by Redis or another durable queue.
- Distributed worker leases.
- OpenTelemetry exporters.
- Prometheus metrics endpoint.
- Persisted eval runs and eval API.
- OpenAI embeddings.
- pgvector-native vector store.
- Hybrid retrieval with BM25.
- RRF and reranking.
- Query rewriting.
- Semantic memory retrieval.
- Automatic memory writes and consolidation.
- S3/MinIO object storage backend.
- Secrets manager integration.
- Remote sandbox execution.
- Visual regression testing.
- Accessibility automation.
- Cross-browser Playwright matrix.

## Non-Goals for v0.1

v0.1 intentionally does not try to be:

- A public multi-tenant SaaS.
- A fully managed cloud platform.
- A general no-code agent builder.
- A chat-only demo.
- A replacement for production identity, secrets, and network controls.
