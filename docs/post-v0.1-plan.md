# Post-v0.1 Completion Plan

Agent Kernel v0.1.0 is published as the first public runtime foundation.

This document defines the completion path from v0.1.0 to Public Alpha, Beta,
and v1.0. It is the source of truth for post-v0.1 scope. Daily plans should
continue to live in `docs/daily/day-XX.md` and should be created just in time.

## Current Status

```text
v0.1.0: Published
Current track: Public Alpha hardening
Next major target: v1.0 production-ready open-source release
```

v0.1.0 already includes:

- API, CLI, worker, and Web Workbench.
- LLM provider abstraction, mock/replay/OpenAI providers, and model routing.
- Prompt versioning foundation.
- Run lifecycle, run events, and worker execution.
- Tool registry, schema validation, policy decisions, and human approvals.
- Approval interrupt/resume, retry, and fallback.
- RAG ingestion, chunking, indexing, retrieval, citations, and `kb_search`.
- Scoped memory CRUD, retrieval, and agent context injection.
- Structured logs, trace IDs, metrics foundation, and deterministic evals.
- Docker Compose stack, examples, release docs, and CI.

v0.1.0 is not v1.0 because it still lacks the production contract expected from
a stable open-source runtime: stable APIs, complete live Web operations,
identity and authorization, stronger durable execution, operational telemetry
exporters, storage backends beyond local defaults, and real user feedback.

## Stage Summary

The post-v0.1 plan is intentionally split by user confidence level:

```text
Day 39-51: Public Alpha answers "Can other developers try it successfully?"
Day 52-75: Beta answers "Can serious teams pilot it safely?"
Day 76-90: v1.0 RC answers "Can the project make stable commitments?"
```

This scope is enough for v1.0. The project should not expand into a hosted SaaS,
general no-code builder, or broad marketplace before v1.0. The remaining work
should harden the runtime that already exists: usability, durability, security,
observability, storage backends, real provider integrations, eval persistence,
and live operator workflows.

## Completion Philosophy

Do not restart the project after v0.1. The right path is iterative hardening:

```text
v0.1.0 foundation -> Public Alpha usability -> Beta production hardening -> v1.0 stability
```

Every post-v0.1 phase should preserve these rules:

- Keep API, CLI, worker, and Web behavior aligned.
- Add tests with every behavior change.
- Update docs whenever user-facing behavior changes.
- Prefer replacing fixture-backed surfaces with live API integration before
  adding new product areas.
- Treat security, persistence, and observability as release blockers for v1.0,
  not optional polish.
- Avoid building a general no-code SaaS or chat-only demo.

## Stage 1: Public Alpha Hardening

Suggested days:

```text
Day 39-51
```

Goal:

```text
An early external user can clone, run, inspect, test, and report useful feedback
without maintainer hand-holding.
```

Must complete:

- Create public feedback channels and issue templates.
- Update README with current release status and clear first-run path.
- Verify fresh-clone backend, Web, and Compose paths on a clean machine.
- Convert the most important Web Workbench views from fixture-backed to live API
  backed where the backend already supports the workflow.
- Improve examples for mock run, approvals, RAG, memory, and evals.
- Expand deterministic behavior evals around retrieval, approvals, retries, and
  memory context injection.
- Improve error messages for common setup and runtime failures.
- Keep dependency audit findings reviewed and documented.
- Add a Public Alpha release note or announcement draft.

Should complete if time allows:

- Add screenshot or short GIF assets for the Workbench.
- Add small seed/demo dataset for RAG and memory examples.
- Add API collection examples.
- Add more troubleshooting cases from user feedback.

Exit criteria:

- A new user can follow the README and quickstart successfully.
- GitHub CI is green on `master`.
- Full Docker Compose startup is verified from a clean checkout.
- Known limitations are clearly listed.
- At least one external-user feedback path is documented.

## Stage 2: Beta Production Hardening

Suggested days:

```text
Day 52-75
```

Goal:

```text
Agent Kernel becomes credible for internal production pilots and serious
extension by other developers.
```

Must complete:

- Authentication baseline.
- Authorization/RBAC baseline.
- Tenant or workspace scoping model.
- Provider-native function calling support.
- Durable model/tool/model execution loop.
- Persisted tool-call records and replayable tool outcomes.
- Redis-backed queue or another durable queue implementation.
- Worker leasing, retry visibility, and stuck-run recovery.
- OpenTelemetry exporter configuration.
- Prometheus-compatible metrics endpoint.
- S3/MinIO object storage backend.
- pgvector-native vector store.
- OpenAI embeddings backend.
- Persisted eval runs and eval API.
- Live Web integration for core operator workflows.
- Migration tests against SQLite and Postgres.

Should complete if time allows:

- Hybrid retrieval with BM25.
- RRF and reranking.
- Query rewriting.
- Semantic memory retrieval.
- Automatic memory writes and consolidation.
- Basic visual regression tests.
- Accessibility checks for the Workbench.

Exit criteria:

- Runtime execution is durable across worker restarts.
- Core state is inspectable through API, CLI, and Web.
- Security boundaries are explicit and tested.
- Telemetry can be exported to common production tools.
- RAG can run with real embeddings and pgvector.
- Storage backends can be switched by configuration.

## Stage 3: v1.0 Release Candidate

Suggested days:

```text
Day 76-90
```

Goal:

```text
Freeze the stable production contract and remove surprises before v1.0.
```

Must complete:

- Freeze public API and CLI compatibility rules.
- Write upgrade and migration policy.
- Add versioned configuration documentation.
- Add backup and restore guidance for Postgres and object storage.
- Add security hardening checklist.
- Add load and soak test scenarios.
- Add release-blocking eval suites.
- Add release-blocking smoke tests for API, worker, Web, RAG, memory, approvals,
  and tool execution.
- Create v1.0 release checklist.
- Create v1.0 release notes.
- Run a full clean-machine release rehearsal.

Should complete if time allows:

- Cross-browser Playwright matrix.
- Performance budget dashboard.
- Plugin or extension authoring guide.
- Public architecture diagrams.

Exit criteria:

- The project has a documented compatibility contract.
- A maintainer can reproduce the release from a clean checkout.
- Critical paths pass automated tests and evals.
- Known limitations are acceptable for a stable open-source runtime.
- v1.0 docs match actual behavior.

## v1.0 Must-Have Scope

v1.0 must include:

- Stable API and CLI for the core runtime.
- Durable run execution.
- Durable tool-call records.
- Human approval and interrupt/resume that survive process restarts.
- Production-grade auth and permission boundaries.
- Configurable storage backends for database, object storage, and vector search.
- Real provider-native tool calling.
- Real embeddings path.
- Live Web Workbench for core operations.
- OpenTelemetry and Prometheus-compatible observability.
- Persisted eval runs and regression gates.
- Security, deployment, backup, and upgrade documentation.

## v1.0 Production Capability Checklist

Use this table to track the major production-grade capabilities that remain
after v0.1.0.

| Capability | Target Stage | Why It Matters | v1.0 Acceptance |
| --- | --- | --- | --- |
| Provider-native function calling | Beta | Real providers return tool calls differently from the internal mock loop. The runtime must support provider-native semantics without leaking provider-specific schemas into domain logic. | OpenAI-style native tool calls can be parsed, persisted, executed through the internal tool model, and covered by deterministic tests. |
| Durable execution | Beta | Production agent runs must survive worker crashes, process restarts, and retry boundaries. | Queued and in-progress runs can recover safely after worker restart without losing state or double-executing unsafe work. |
| Persisted tool calls and approvals | Beta | Operators need an auditable record of tool inputs, outputs, risk decisions, approvals, rejections, and resumes. | Tool calls and approval decisions are stored, inspectable through API/CLI/Web, and linked to run events and trace IDs. |
| Auth, RBAC, and workspace scope | Beta | A self-hosted runtime still needs explicit identity, permission, and isolation boundaries before serious use. | Users, roles, permissions, and workspace-scoped resources are enforced by API tests and documented. |
| Real embeddings and pgvector | Beta | RAG needs a real embedding backend and production-shaped vector storage path. | A knowledge base can index with real embeddings, store vectors in pgvector, and retrieve through the configured vector backend. |
| S3/MinIO object storage | Beta | Uploaded documents should not depend only on local filesystem storage. | Object storage can be switched between local and S3-compatible backends through configuration and tested with MinIO. |
| OpenTelemetry and Prometheus | Beta | Production operators need traces and metrics outside process-local logs. | Traces can be exported through OpenTelemetry, and runtime metrics are exposed through a Prometheus-compatible endpoint. |
| Persisted evals | Beta | Agent behavior quality must be tracked over time, not only printed to the CLI. | Eval runs, cases, scores, failures, and metadata are persisted and queryable through API/CLI. |
| Live Web Workbench | Public Alpha and Beta | The Workbench should become a real operator console rather than a fixture-backed preview. | Core run, approval, knowledge, memory, and eval workflows use live backend APIs with smoke tests. |
| Upgrade, backup, and security docs | v1.0 RC | v1.0 needs an operational contract, not only feature completeness. | Upgrade policy, migration policy, backup/restore guide, security hardening checklist, and release checklist exist and match behavior. |

## Explicitly Deferred Beyond v1.0

These are valuable, but should not block v1.0:

- Public hosted SaaS.
- Multi-region cloud deployment.
- Marketplace of third-party tools.
- Visual no-code workflow builder.
- Advanced multi-agent marketplace.
- Full enterprise SSO.
- Fine-grained billing system.
- Large-scale benchmark leaderboard.

## Major Risks and Tradeoffs

Risk: v1.0 scope can become too broad.

Mitigation:

- Treat v1.0 as a stable self-hosted runtime, not a SaaS platform.
- Move non-core product ideas beyond v1.0.

Risk: Web UI can consume too much time.

Mitigation:

- Prioritize live operator workflows over decorative polish.
- Keep API and CLI authoritative.

Risk: provider-native function calling can complicate the runtime loop.

Mitigation:

- Preserve a provider-neutral internal tool-call model.
- Add provider adapters without leaking provider-specific schemas into domain
  logic.

Risk: durable execution can become a workflow-engine project.

Mitigation:

- Implement the smallest durable run loop first.
- Add external workflow engines only after the internal lifecycle is stable.

Risk: security work can be postponed too long.

Mitigation:

- Make auth, RBAC, tenant/workspace scoping, audit logs, and permission tests
  Beta blockers.

## Next Daily Work

The next normal work item should be:

```text
Day 39: Public Alpha kickoff
```

Suggested Day 39 focus:

- Update release status docs after v0.1.0 publication.
- Create Public Alpha tracking structure.
- Add issue templates for bug reports, feature requests, and early-user
  feedback.
- Audit README and quickstart for first external users.
- Decide which Web Workbench views should become live API backed first.
