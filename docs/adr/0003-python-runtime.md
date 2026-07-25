# ADR 0003: Use Python for Agent Runtime and TypeScript for Web UI

## Status

Accepted

## Context

Agent Kernel's core work is agent runtime execution, LLM integration, RAG, memory, evals, document ingestion, tool orchestration, observability, and worker execution. These areas are strongly supported by the Python AI ecosystem.

The Web UI still benefits from TypeScript and the React ecosystem.

## Decision

Use Python for:

- Agent runtime.
- API server.
- Worker.
- CLI.
- RAG.
- Memory.
- Evals.
- Provider integrations.

Use TypeScript for:

- Next.js Web UI.
- Frontend API client.
- Browser-based operational views.

## Consequences

Benefits:

- Lower friction for LLM/RAG/eval implementation.
- Better fit for AI engineering workflows.
- Strong frontend stack without forcing Node.js into runtime responsibilities.

Costs:

- Two-language monorepo.
- Need root-level commands that make backend and frontend development coherent.
- Need clear API contracts between FastAPI and Next.js.
