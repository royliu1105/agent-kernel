# API and CLI Compatibility Policy

This document defines the v1.0 release candidate contract baseline for Agent
Kernel public interfaces.

The goal is to make self-hosted users and extension authors comfortable building
against Agent Kernel without freezing every internal implementation detail.

## Stability Levels

Stable:

- Intended to remain compatible across v1.x releases.
- Breaking changes require a major version bump unless a security issue makes
  that impossible.
- Additive changes are allowed.
- Documented request fields, response fields, command names, option names, exit
  code semantics, and environment variables are part of the contract.

Preview:

- Available for early operator feedback.
- May change during the v1.0 RC track or a later minor release.
- Must be documented as preview where it appears.
- Should not be used as the only automation path for production workflows.

Internal:

- No compatibility guarantee.
- Used by implementation code, tests, local development, or same-origin Web
  proxying.
- Can change without deprecation when it is not exposed as a public API or CLI
  command.

Deferred:

- Planned or valuable, but not part of the current v1.0 contract.
- Must not appear in release notes as an implemented feature.

## Compatibility Rules

Stable HTTP API rules:

- Keep stable endpoint paths and HTTP methods compatible.
- Keep required request fields compatible.
- Do not remove documented response fields.
- Prefer adding optional request fields and nullable or optional response fields.
- Preserve status-code families for common outcomes.
- Keep error responses JSON-shaped with a meaningful `detail` value.
- Keep authentication and authorization failures explicit with 401 or 403.
- Do not change identifier formats without a major version.

Stable CLI rules:

- Keep command groups and command names compatible.
- Keep documented option names compatible.
- Preserve JSON output shapes for automation-oriented commands.
- Preserve non-zero exit behavior for failed eval reports when
  `--fail-on-failure` is active.
- Prefer additive options over changing existing option semantics.
- Deprecate before removing commands or options unless a security issue requires
  immediate removal.

Stable worker rules:

- Keep documented worker command flags compatible.
- Preserve the meaning of `--once`, `--loop`, `--limit`, `--poll-interval`, and
  `--recover-stuck`.
- Keep the database as the durable source of truth for v1.0 unless the
  compatibility policy is updated before release.

Deprecation rules:

- Mark deprecated stable surfaces in docs and release notes.
- Keep deprecated stable surfaces for at least one minor release where
  practical.
- Provide the replacement path before removal.
- Tests should cover deprecated behavior until it is removed.

## Stable HTTP API

Health and metrics:

```http
GET /healthz
GET /metrics
```

Agents and runs:

```http
POST /v1/agents
GET  /v1/agents/{agent_id}
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/queue
POST /v1/runs/{run_id}/cancel
POST /v1/runs/{run_id}/resume
```

Approvals:

```http
GET  /v1/approvals
GET  /v1/approvals/{approval_id}
POST /v1/approvals/{approval_id}/approve
POST /v1/approvals/{approval_id}/reject
```

Knowledge bases, documents, chunks, embeddings, and retrieval:

```http
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
POST /v1/knowledge-bases/{knowledge_base_id}/retrieve
POST /v1/knowledge-bases/{knowledge_base_id}/documents
POST /v1/knowledge-bases/{knowledge_base_id}/documents/upload
GET  /v1/knowledge-bases/{knowledge_base_id}/documents
GET  /v1/documents/{document_id}
POST /v1/documents/{document_id}/ingest
GET  /v1/documents/{document_id}/ingestion-jobs
GET  /v1/ingestion-jobs/{job_id}
POST /v1/documents/{document_id}/chunk
GET  /v1/documents/{document_id}/chunks
GET  /v1/document-chunks/{chunk_id}
POST /v1/documents/{document_id}/index
GET  /v1/documents/{document_id}/embeddings
```

Memory:

```http
POST   /v1/memory
GET    /v1/memory
GET    /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

Eval runs:

```http
POST /v1/evals/runs
GET  /v1/evals/runs
GET  /v1/evals/runs/{eval_run_id}
```

## Stable CLI

The stable CLI binary is:

```bash
agent-kernel
```

Stable command groups:

```bash
agent-kernel agent
agent-kernel run
agent-kernel approval
agent-kernel kb
agent-kernel document
agent-kernel ingestion
agent-kernel chunk
agent-kernel embedding
agent-kernel memory
agent-kernel eval
```

Stable commands:

```bash
agent-kernel agent create
agent-kernel run create
agent-kernel run inspect
agent-kernel run events
agent-kernel run queue
agent-kernel run cancel
agent-kernel run resume

agent-kernel approval list
agent-kernel approval inspect
agent-kernel approval approve
agent-kernel approval reject

agent-kernel kb create
agent-kernel kb list
agent-kernel kb inspect
agent-kernel kb search

agent-kernel document register
agent-kernel document upload
agent-kernel document list
agent-kernel document inspect
agent-kernel document ingest
agent-kernel document chunk
agent-kernel document index

agent-kernel ingestion inspect
agent-kernel ingestion list

agent-kernel chunk list
agent-kernel chunk inspect

agent-kernel embedding list

agent-kernel memory create
agent-kernel memory list
agent-kernel memory inspect
agent-kernel memory delete

agent-kernel eval report
```

Stable worker binary:

```bash
agent-kernel-worker
```

Stable worker modes:

```bash
agent-kernel-worker --once --limit 10
agent-kernel-worker --loop --limit 25 --poll-interval 2
agent-kernel-worker --recover-stuck --limit 100
```

## Preview Surfaces

The following surfaces are available but not yet part of the final v1.0 stable
contract:

- Same-origin Web proxy routes under `/api/agent-kernel/*`.
- Web Workbench layout, labels, and visual organization.
- Redis queue adapter APIs as direct library extension points.
- OpenTelemetry SDK wiring details beyond documented environment variables.
- Internal Pydantic and SQLAlchemy model class names.
- Migration revision names before the v1.0 final tag.

## Deferred Public Surfaces

These are explicitly outside the current contract:

```http
GET    /v1/runs
PATCH  /v1/agents/{agent_id}
DELETE /v1/agents/{agent_id}
POST   /v1/runs/{run_id}/retry
POST   /v1/evals/datasets
GET    /v1/evals/datasets
POST   /v1/evals/jobs
GET    /v1/evals/jobs/{job_id}
```

Deferred product capabilities:

- Server-side eval job execution.
- Redis-first worker scheduling as the default execution path.
- Hosted multi-tenant SaaS isolation.
- Public browser session automation.
- Hybrid retrieval, RRF, reranking, and query rewriting as stable APIs.

## v1.0 RC Review Rules

During Day 76-90:

- Any new public endpoint must be added to this policy.
- Any removed endpoint must be removed from `docs/interfaces.md` and release
  notes before v1.0.
- Any promoted preview surface must gain tests and user-facing docs.
- Any unstable behavior that remains must be listed in v1.0 known limitations.
