# User Experience

## UX Positioning

Agent Kernel should not become a generic chatbot UI.

The intended product experience is:

```text
Agent Workbench
```

Chat is supported, but it is only one way to start or continue a task. The core UX is about creating, running, observing, approving, evaluating, and managing agents.

## Product Experience Layers

The user experience has three layers:

```text
1. Task Input
2. Run Workspace
3. Control Plane
```

### Task Input

This can look like chat:

- A user gives an agent a task.
- A user adds context.
- A user asks a follow-up question.
- A user requests a rerun or refinement.

The task input surface should not hide the execution process.

### Run Workspace

This is the core experience.

The user should see what the agent did:

- Run started.
- Model planned next action.
- Retrieval ran.
- Tool was requested.
- Tool executed.
- Approval was requested.
- Run paused.
- User approved or rejected.
- Run resumed.
- Final answer produced.

The run workspace should be timeline-first.

### Control Plane

This is where users manage the runtime:

- Agents.
- Prompts.
- Model policies.
- Tools.
- Permissions.
- Memory.
- Knowledge base.
- Approvals.
- Evals.
- Settings.

## Primary Navigation

MVP navigation should be:

```text
Dashboard
Agents
Runs
Approvals
Knowledge
Evals
Settings
```

## Dashboard

The dashboard should show:

- Recent runs.
- Running, succeeded, failed, and waiting-approval counts.
- Average latency.
- Total estimated cost.
- Recent errors.
- Pending approvals.
- Recent eval results.

The dashboard is the default home screen. The default home screen should not be a blank chat page.

## Agents

The Agents area should support:

- Agent list.
- Agent detail.
- Agent configuration.
- Prompt version.
- Model policy.
- Tool permissions.
- Memory policy.
- Knowledge base binding.
- Eval baseline.

An agent detail page may include a task input panel, but configuration and runs remain first-class.

## Runs

The Run detail page is the most important UX surface.

It should show:

- Final result.
- Timeline.
- Step details.
- Model calls.
- Tool calls.
- Retrievals.
- Citations.
- Approval decisions.
- Errors and retries.
- Token usage.
- Estimated cost.
- Trace ID.

The layout should make the execution process understandable, not just display the final answer.

## Task Input and Chat

Agent Kernel can include a chat-like task input:

```text
Ask this agent to do something...
```

But the surrounding UI should expose:

- Timeline.
- Tool calls.
- Citations.
- Cost.
- Trace.
- Approval status.
- Eval or regression context where relevant.

Chat is the input mode. The runtime timeline is the product differentiator.

## Approvals

Approval UX should be explicit and operational.

When an agent requests a risky tool call, the user should see:

- Tool name.
- Tool arguments.
- Risk level.
- Policy reason.
- Expected side effect.
- Run context.
- Approve action.
- Reject action.
- Decision note.

The approval inbox should feel like an operational review queue, not a chat message.

## Knowledge Base

The Knowledge area should show:

- Uploaded documents.
- Ingestion status.
- Chunk count.
- Embedding status.
- Retrieval playground.
- Citation sources.

Users should be able to understand whether retrieval quality problems come from ingestion, chunking, embedding, retrieval, or prompting.

## Evals

The Evals area should show:

- Eval datasets.
- Eval runs.
- Pass/fail summary.
- Failed cases.
- Tool call diffs.
- Citation failures.
- Cost changes.
- Step count changes.
- Prompt version changes.

The goal is to make agent behavior regression visible.

## UX Non-Goals

MVP should not prioritize:

- A consumer-style assistant interface.
- A marketing landing page.
- Decorative chat-first design.
- Social or team collaboration features.
- A visual workflow builder.
- A plugin marketplace.

These may come later only if they support the Agent Workbench experience.

## Success Criteria

The UX succeeds when a user can answer:

- What did the agent do?
- Why did it do that?
- Which model did it call?
- Which tools did it call?
- What did it retrieve?
- What needs approval?
- What failed?
- How much did it cost?
- Did behavior regress?

## Core Principle

Agent Kernel's UI should make agent execution controllable and explainable.

It should feel like:

```text
A control console for real agent work
```

Not:

```text
A generic chatbot clone
```
