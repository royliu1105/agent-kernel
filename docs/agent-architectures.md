# Agent Architectures

## Purpose

This document maps the mainstream AI Agent architecture patterns that Agent Kernel should understand and selectively support.

Agent Kernel should not implement every pattern equally in v0.1. The project should use these patterns deliberately, with a production runtime as the organizing center.

## Architecture Map

Mainstream Agent architectures can be grouped into:

```text
Single-agent patterns
Workflow/state-machine patterns
Retrieval and memory patterns
Human-control patterns
Multi-agent patterns
Production runtime patterns
```

## 1. Single LLM Call

Shape:

```text
User Input -> LLM -> Answer
```

Use cases:

- Classification.
- Rewriting.
- Summarization.
- Simple Q&A.

Limitations:

- No tool use.
- No persistent state.
- No execution loop.
- No recovery.

Agent Kernel should support this as the simplest run shape, but it is not the main product differentiator.

## 2. Tool-Calling Agent

Shape:

```text
User Input
  -> LLM chooses tool call
  -> Tool executes
  -> LLM observes result
  -> Final answer
```

Use cases:

- Database query.
- API calls.
- Knowledge base search.
- Safe bounded actions.

Agent Kernel v0.1 should support this pattern directly through:

- `LLMProvider`.
- `ToolRegistry`.
- `ToolExecutor`.
- `ToolCall`.
- Policy evaluation.
- Run timeline.

## 3. ReAct Agent

Shape:

```text
Thought -> Action -> Observation -> Thought -> Action -> Observation -> Final
```

Use cases:

- Search tasks.
- Debugging.
- Investigation.
- Multi-step tool use.
- Research tasks.

Risks:

- Infinite loops.
- Cost blowups.
- Error accumulation.
- Harder deterministic testing.

Agent Kernel should support a bounded ReAct-style loop with:

- Maximum step count.
- Retry limits.
- Tool permissions.
- Cost tracking.
- Behavior evals.
- Traceable step history.

## 4. Plan-and-Execute Agent

Shape:

```text
Planner -> Plan -> Executor -> Results -> Replanner -> Final
```

Use cases:

- Long tasks.
- Research and report generation.
- Runbook execution.
- Multi-step workflows.

Risks:

- Plans become stale.
- Over-planning increases cost.
- Replanning can loop.

Agent Kernel should support this as a runtime strategy after the base run lifecycle and tool loop are stable.

## 5. Workflow / State Machine Agent

Shape:

```text
State A -> State B -> State C
       -> approval
       -> retry
       -> fallback
```

Use cases:

- Approval workflows.
- RAG pipelines.
- Customer support flows.
- Operations flows.
- Enterprise internal agents.

This is Agent Kernel's core production architecture.

The runtime should make state explicit:

- Run states.
- Step states.
- Tool call states.
- Approval states.
- Retry/fallback states.
- Recovery points.

## 6. Graph-Based Agent

Shape:

```text
Node = LLM / Tool / Retriever / Human / Sub-agent
Edge = condition / state transition
State = shared runtime state
```

Use cases:

- Complex workflows.
- Conditional branching.
- Loops.
- Human-in-the-loop.
- Multi-agent workflows.

Agent Kernel v0.1 should start with a simple state machine. Later versions may introduce a graph abstraction and visual workflow tooling.

## 7. Reflection / Critic Agent

Shape:

```text
Actor -> Result
Critic -> Review
Actor -> Revise
```

Alternative:

```text
Run -> Feedback -> Reflection Memory -> Next Attempt
```

Use cases:

- Code generation.
- Writing.
- Complex reasoning.
- Failure recovery.
- Eval-driven improvement.

Risks:

- Self-critique can be unreliable.
- Extra token cost.
- May hide rather than fix root cause.

Agent Kernel should treat reflection as optional and eval-informed, not as a default magic fix.

## 8. RAG Agent

Shape:

```text
User Query
  -> Retrieve documents
  -> Rerank/filter
  -> LLM answer with citations
```

Agentic shape:

```text
Agent decides when to search
Agent calls kb_search
Agent cites sources
Agent asks follow-up if context is insufficient
```

Use cases:

- Knowledge base Q&A.
- Document analysis.
- Internal assistant.
- Research assistant.

Agent Kernel v0.1 should support RAG through:

- Document ingestion.
- Chunking.
- Embeddings.
- pgvector retrieval.
- `kb_search` tool.
- Citations.
- RAG evals.

## 9. Human-in-the-Loop Agent

Shape:

```text
Agent proposes action
Policy checks risk
Human approves/rejects
Agent resumes/stops
```

Use cases:

- Sending email.
- Modifying code.
- Deployment.
- Deleting data.
- Calling external systems.
- Financial, legal, or production operations.

This is a first-class Agent Kernel capability.

The runtime should support:

- Approval request.
- Run pause.
- Reviewable arguments.
- Decision audit.
- Resume.
- Reject/stop behavior.

## 10. Multi-Agent Supervisor

Shape:

```text
User
 -> Supervisor
    -> Research Agent
    -> Coding Agent
    -> Review Agent
    -> Writer Agent
 -> Final
```

Use cases:

- Task decomposition.
- Multi-role collaboration.
- Complex research.
- Software engineering workflows.

Risks:

- High cost.
- Hard debugging.
- Context handoff complexity.
- Responsibility overlap.

Agent Kernel should not lead with this in v0.1. It should add supervisor-style multi-agent coordination after the single-agent runtime is reliable.

## 11. Multi-Agent Handoff / Swarm

Shape:

```text
Agent A -> handoff to Agent B -> handoff to Agent C
```

Use cases:

- Customer support routing.
- Expert systems.
- Multi-domain tasks.
- Long-running conversations.

Risks:

- Control flow confusion.
- Looping handoffs.
- Unclear ownership.
- Harder evals.

Agent Kernel should eventually support explicit handoff payloads, ownership, and loop limits.

## 12. Event-Driven / Durable Agent Runtime

Production shape:

```text
API creates run
DB persists state
Queue schedules work
Worker executes step
State checkpointed
Failures retry/resume
Human approval interrupts
Observability records trace/cost
```

Use cases:

- Real deployments.
- Long tasks.
- Background execution.
- Recoverable agents.
- Enterprise agent platforms.

This is the production runtime architecture Agent Kernel should implement.

MVP:

- DB-backed run state.
- Redis queue.
- Worker process.
- Retry and resume semantics.

Later:

- Temporal durable execution adapter.

## Agent Kernel Architecture Choice

Agent Kernel should combine patterns this way:

```text
Core runtime:
  Workflow / State Machine Agent

Execution loop:
  Tool-Calling + bounded ReAct-style loop

Complex tasks:
  Plan-and-Execute

Knowledge:
  RAG Agent

Safety:
  Human-in-the-Loop Agent

Quality:
  Reflection / Critic only when eval-informed

Later collaboration:
  Multi-Agent Supervisor + explicit Handoff

Production execution:
  Event-driven durable worker architecture
```

## v0.1 Implementation Priority

MVP must prioritize:

1. Run lifecycle.
2. Tool calling.
3. Human approval and resume.
4. RAG.
5. Memory.
6. Observability.
7. Evals.

MVP should not prioritize:

- Complex autonomous multi-agent systems.
- Unbounded ReAct loops.
- Swarm routing.
- Reflection as a default behavior.
- Visual workflow builders.

## Core Principle

Agent Kernel should not be an agent gimmick collection.

It should be:

```text
A stateful, observable, recoverable runtime that can host multiple agent architecture patterns safely.
```
