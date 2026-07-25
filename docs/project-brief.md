# Project Brief

## Project Name

Agent Kernel

## One-Sentence Positioning

Agent Kernel is a self-hosted, observable, evaluable, resumable production-grade AI Agent Runtime for building real agent applications with tools, memory, knowledge bases, human approval, and workflows.

## Goals

1. Build a real production-grade open-source AI Agent project.
2. Use the project to systematically develop senior-level AI Agent engineering ability.
3. Create a deployable, testable, maintainable, extensible, community-usable runtime.

## Non-Goals

Agent Kernel is not:

- A toy project.
- A course assignment.
- A simple chat demo.
- A LangChain wrapper.
- A generic model training platform.
- An AutoGPT-style unconstrained autonomous bot.
- A full enterprise SaaS platform in v0.1.
- A plugin marketplace in v0.1.

## Recommended Direction

Three candidate directions were considered:

1. General production-grade Agent Runtime.
2. DevOps/SRE operations agent.
3. Knowledge-base and task workflow agent.

The selected direction is:

```text
Agent Kernel = General Agent Runtime + official examples
```

This gives the project enough breadth to cover production Agent engineering while allowing concrete examples such as RAG agents, approval agents, tool agents, and research agents.

## Target Users

MVP target users:

- AI application engineers.
- Backend engineers building internal agent systems.
- Developers learning production-grade AI Agent architecture.
- Small teams that need a self-hosted agent runtime.

Later target users:

- Platform teams.
- SRE and DevOps teams.
- SaaS teams embedding agents into products.
- Tool/plugin authors.

## Core Scenarios

MVP scenarios:

- Create an agent with model policy, prompt version, tools, memory policy, and permissions.
- Start a run and let a worker execute it.
- Let the agent call registered tools through a validated tool schema.
- Pause a run when a risky tool call requires human approval.
- Approve, reject, resume, retry, or cancel a run.
- Upload documents, ingest them, retrieve knowledge chunks, and cite sources.
- Track run timeline, model calls, tool calls, token usage, cost, errors, and traces.
- Run deterministic behavior evals against mock or replay providers.
- Operate through API, CLI, and Web UI.

## MVP Required Capabilities

- LLM provider abstraction.
- Model routing.
- Tool calling and function calling.
- Agent planning and execution loop.
- Workflow graph or state machine.
- Short-term memory.
- Task context.
- User preferences.
- Long-term memory.
- RAG, knowledge base, and document ingestion.
- Multi-agent collaboration and handoff baseline.
- Human-in-the-loop approval.
- Interrupt and resume.
- Guardrails, permissions, sandbox baseline, and security policy.
- Observability: traces, logs, metrics, and cost tracking.
- Evals: unit, integration, behavior, and regression.
- Prompt and version management.
- Error recovery, retries, and fallback.
- Async task queue and durable run state.
- API server, CLI, and Web UI.
- Authentication baseline.
- Docker Compose deployment.
- CI/CD.
- Documentation, examples, contribution guide, and roadmap.

## Later Enhancements

- Temporal durable execution adapter.
- Advanced multi-agent collaboration.
- MCP tool integration.
- Qdrant or Weaviate vector store adapter.
- S3 or MinIO object storage production mode.
- OIDC and SSO.
- OPA/Rego policy engine.
- Kubernetes and Helm deployment.
- Advanced eval dashboard.
- Workflow graph editor.
- Plugin/tool marketplace.
- Prompt playground.
