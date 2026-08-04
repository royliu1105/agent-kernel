# Public Alpha Guide

Agent Kernel is currently moving from the published `v0.1.0` foundation into
Public Alpha hardening.

Public Alpha is not a new product direction. It is the phase where the existing
runtime is made easier for early users to try, inspect, and critique.

## Current Status

```text
Current release: v0.1.0
Current track: Public Alpha hardening
Primary goal: make first-run experience and feedback loops reliable
```

Start here:

- [README](../README.md)
- [Quickstart](quickstart.md)
- [Troubleshooting](troubleshooting.md)
- [v0.1 Snapshot](v0.1.md)
- [Post-v0.1 Completion Plan](post-v0.1-plan.md)

## What Early Users Should Try

Recommended first-run order:

1. Install dependencies with `uv sync` and `npm install`.
2. Run the SQLite quick path in [Quickstart](quickstart.md).
3. Create a mock agent run and execute the worker once.
4. Run the RAG workflow.
5. Run the memory workflow.
6. Run the deterministic eval.
7. Open the Web Workbench.
8. Try the full Docker Compose stack if Docker Desktop is available.

This path intentionally uses mock models by default. No external LLM credentials
are required unless users choose an `openai:*` model.

## Feedback Channels

Use GitHub Issues for Public Alpha feedback:

- Bug report: reproducible runtime, setup, API, CLI, Web, Docker, or docs bug.
- Feature request: focused improvement tied to a real workflow.
- Public Alpha feedback: first-run experience, confusing docs, missing examples,
  or operator-workflow gaps.

Good feedback includes:

- Exact commands or UI actions.
- Expected behavior.
- Actual behavior.
- Operating system.
- Python, `uv`, Node.js, Docker, and database versions.
- Release or commit SHA.
- Redacted logs or screenshots when useful.

Do not include secrets, API keys, tokens, private documents, or private logs.

## Public Alpha Priorities

Public Alpha should improve confidence in the existing v0.1 foundation:

- First-run clarity.
- Troubleshooting coverage.
- Example quality.
- Runtime error messages.
- Behavior eval coverage.
- Web Workbench live API integration.
- Dependency and release-risk visibility.

It should not expand Agent Kernel into a hosted SaaS, no-code builder, or broad
marketplace before v1.0.

## Live Web API Priorities

The Workbench currently shows the intended operator-console shape, but much of
the UI is still fixture-backed. The first live API work should follow the
existing backend surface.

Priority 0:

- Health status from `/healthz` through the Web same-origin health proxy.
- Run detail from `/v1/runs/{run_id}`.
- Run timeline from `/v1/runs/{run_id}/events`.

Current status:

- Health status is implemented in the Workbench topbar through
  `/api/agent-kernel/health`.
- Run detail and run timeline live integration remain next.

Priority 1:

- Approval inbox from `/v1/approvals`.
- Approve and reject actions through `/v1/approvals/{approval_id}/approve` and
  `/v1/approvals/{approval_id}/reject`.
- Knowledge base list from `/v1/knowledge-bases`.
- Retrieval flow through `/v1/knowledge-bases/{knowledge_base_id}/retrieve`.

Priority 2:

- Memory list and detail from `/v1/memory`.
- Document and ingestion job status views.
- Eval report views after eval persistence exists.

Backend gaps to resolve before a fully live Workbench:

- List agents endpoint.
- List runs endpoint.
- Persisted eval run API.
- Better document and ingestion summary endpoints for operator views.

## Public Alpha Exit Criteria

Public Alpha can close when:

- A new user can follow README and Quickstart without maintainer help.
- Core examples are easy to discover and run.
- Full Docker Compose startup is verified from a clean checkout.
- GitHub CI is green on `master`.
- Known limitations are clear.
- Feedback channels are documented and issue templates are available.
- The first live Web API integration path is implemented.
