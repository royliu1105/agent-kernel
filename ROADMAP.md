# Agent Kernel Roadmap

## Current Follow-Up

Use the [Post-v1.0 Capability Hardening Plan](docs/capability-hardening-plan.md)
for current work and status. R1-R10 remediation passed scoped acceptance for
`d65e833` after the earlier blanket acceptance was withdrawn. Subsequent N1-N4
bounded-execution work has local verification; N5 tracks its separate
current-commit CI gate. Evidence and explicit limits live in the canonical plan.
No new release is implied. The earlier release targets below are historical scope, not
evidence that every production guarantee is already implemented.

## Historical Release Targets

Both v0.1.0 and v1.0.0 are published. Public Alpha, Beta and Day 76-90 below
record the historical route to v1.0, not the current development stage.

See [Post-v0.1 Completion Plan](docs/post-v0.1-plan.md) for that historical scope.

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

Status: historical scope complete; see [Public Alpha Summary](docs/public-alpha-summary.md).

Goal:

```text
An early external user can try Agent Kernel, understand the project, report
issues, and give useful feedback without maintainer hand-holding.
```

Original stage scope (historical):

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

Status: historical scope complete; see [Beta Summary](docs/beta-summary.md).

Goal:

```text
Agent Kernel is credible for internal production pilots and serious extension
by other developers.
```

Original stage scope (historical):

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

Status: v1.0.0 published 2026-08-07. See the
[release checklist](docs/v1-release-checklist.md) for the tag, commit and CI evidence.

Goal:

```text
Stable self-hosted production-grade open-source AI Agent runtime.
```

Original v1.0 delivery requirements (subject to the recorded release limitations):

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

Original beyond-v1.0 backlog, not a current pending-work checklist. Some retrieval
and external-tool capabilities have since landed; use the canonical hardening
plan for their implementation status, acceptance and remaining limits.

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
