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

Detailed write policy will be completed during Phase 3C implementation.

## Phase 3C Memory Plan

Phase 3C implements memory foundation after the RAG retrieval path is usable:

```text
Day 22: Memory Domain + Storage + API/CLI
Day 23: Memory Retrieval + Agent Context Integration
```

## Day 22 Memory Domain, Storage, API, and CLI

Day 22 should implement:

- `MemoryItem` domain model.
- Explicit memory types:
  - `short_term`
  - `task_context`
  - `user_preference`
  - `long_term`
- Memory scope fields.
- Memory storage table and migration.
- Repository operations.
- API operations to create, list, inspect, and delete memory.
- CLI operations to create, list, inspect, and delete memory.

Day 22 should not implement agent context injection, semantic memory retrieval, or automatic memory writes.

## Day 23 Memory Retrieval and Agent Context Integration

Day 23 should implement:

- Memory retrieval for scoped memory records.
- User preference retrieval.
- Task context retrieval.
- Agent runtime context injection.
- Run timeline visibility when memory is used.
- Tests for memory context behavior.

Day 23 should not implement autonomous memory consolidation, graph memory, or broad automatic long-term memory writes.

## API / CLI

Expected API:

```http
GET    /v1/memory
POST   /v1/memory
GET    /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

Expected CLI:

```bash
agent-kernel memory create --type user_preference --scope user:<id> --content '{"language":"zh"}'
agent-kernel memory list --scope user:<id>
agent-kernel memory inspect <memory-id>
agent-kernel memory delete <memory-id>
```

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
