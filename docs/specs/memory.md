# Feature Spec: Memory

## Goal

Provide a clear memory system covering short-term context, task context, user preferences, and long-term memory without making memory behavior opaque.

## Non-Goals

- Personality simulation.
- Unbounded autonomous memory writes.
- Graph memory database in v0.1.
- Complex memory consolidation in v0.1.

## User Stories

- As a user, I can persist preferences such as preferred language or output format.
- As an agent, I can retrieve relevant task context.
- As an operator, I can inspect and delete memory items.
- As an evaluator, I can verify whether memory was used appropriately.

## Domain Model

Initial entities:

- `MemoryItem`
- `UserPreference`
- `TaskContext`
- `MemoryQuery`
- `MemoryResult`

Memory types:

```text
short_term
task_context
user_preference
long_term
```

Memory fields:

```text
scope
content
source_run_id
confidence
metadata
created_at
```

## State Transitions

Initial memory lifecycle:

```text
proposed -> written -> retrieved -> updated/deleted
```

Detailed write policy will be completed during Phase 3 implementation.

## API / CLI

Expected API:

```http
GET    /v1/memory
POST   /v1/memory
DELETE /v1/memory/{memory_id}
```

CLI can be added after API semantics settle.

## Failure Modes

- Memory retrieval returns irrelevant items.
- Memory writes duplicate existing facts.
- Memory stores sensitive information.
- Memory conflicts with current user instruction.
- Memory scope is too broad.

## Security

- Memory must have scope.
- Users must be able to inspect and delete memory.
- Sensitive data should not be written by default.
- Current instruction should override stale memory.

## Observability

- Memory read span.
- Memory write span.
- Retrieved memory item IDs.
- Memory type.
- Memory count.

## Test Plan

- Short-term context is available during a run.
- User preference can be written and retrieved.
- Long-term memory can be retrieved by semantic query.
- Memory can be deleted.
- Sensitive data redaction is applied where required.

## Acceptance Criteria

- MVP supports short-term context, task context, user preferences, and long-term memory items.
- Memory is inspectable and scoped.
- Memory use is visible in the run timeline.
