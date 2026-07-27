# ADR 0004: Use Python Runtime with TypeScript Product Surface

## Status

Accepted

## Context

Many strong open-source Agent projects are TypeScript-first. This is especially common for personal assistants, chat-centric products, MCP-heavy tools, desktop/web assistants, and multi-channel agent products.

Examples in the broader ecosystem include TypeScript projects oriented around:

- Web and React interfaces.
- Node.js runtimes.
- MCP tools.
- Chat and streaming UX.
- Browser and desktop integrations.
- Personal assistant workflows.
- npm-based distribution.

This creates a valid concern: Agent Kernel should not ignore the TypeScript Agent ecosystem.

However, Agent Kernel's current product goal is not to build a chat-first personal assistant. The goal is to build a production-grade Agent runtime and workbench:

- Durable run state.
- Worker execution.
- Tool calling.
- Human approval and resume.
- RAG and document ingestion.
- Memory.
- Evals.
- Observability.
- Cost tracking.
- Storage architecture.
- API, CLI, and Web control plane.

These runtime-heavy responsibilities align well with Python's AI, backend, RAG, eval, and data-processing ecosystem.

## Decision

Use this language strategy:

```text
Python owns the runtime.
TypeScript owns the product surface.
```

Python is used for:

- Agent runtime.
- API server.
- Worker.
- CLI.
- Provider abstraction.
- Tool execution.
- RAG.
- Memory.
- Evals.
- Observability.
- Storage adapters.

TypeScript is used for:

- Web UI.
- Agent Workbench control console.
- Run timeline.
- Approval inbox.
- Knowledge and eval views.
- Future API client.
- Future TypeScript SDK or integration examples.

Agent Kernel is therefore:

```text
Python-first runtime
TypeScript-first interface
```

It is not:

```text
Python-only ecosystem
TypeScript-only agent app
```

## Why Not TypeScript-First Runtime Now

TypeScript would be a better primary runtime choice if Agent Kernel were primarily:

- A personal assistant.
- A chat-first product.
- A desktop assistant.
- A multi-channel messaging assistant.
- A Vercel/Next.js-first SaaS app.
- A primarily MCP/npm plugin ecosystem.
- A product for TypeScript developers only.

That is not the current target.

For Agent Kernel v0.1, the deeper engineering work is:

- State machines.
- Durable run state.
- RAG pipelines.
- Eval infrastructure.
- Worker execution.
- Storage/repository design.
- Observability.
- Cost and behavior tracking.

Python gives lower friction for these areas.

## Consequences

Benefits:

- Strong fit for AI runtime, RAG, evals, and backend worker development.
- Strong FastAPI/Pydantic/SQLAlchemy ecosystem for production backend design.
- Strong TypeScript/Next.js ecosystem for the Agent Workbench UI.
- Clear separation between runtime semantics and product interface.
- Leaves room for TypeScript SDK and integrations later.

Costs:

- Two-language monorepo.
- API contracts must be kept clean between Python and TypeScript.
- Frontend and backend dependency management must both be maintained.
- TypeScript Agent ecosystem integrations require explicit adapters or examples.

## Follow-Up Options

Later versions may add:

- TypeScript API client.
- TypeScript SDK.
- MCP tool examples in TypeScript.
- Vercel AI SDK example UI.
- OpenAI Agents JS integration example.
- TypeScript worker/tool adapter for teams that prefer Node.js.

These should extend the project without moving the v0.1 runtime away from Python.

## Review Trigger

Revisit this decision if:

- Most contributors strongly prefer TypeScript.
- The product shifts toward a personal assistant or chat-first app.
- Runtime-heavy Python modules remain thin while TypeScript UI becomes the main product.
- The project prioritizes MCP/npm plugin distribution over backend runtime semantics.
- Production deployments require Node.js-first integration.
