# Feature Specs

This directory will hold lightweight specs for core Agent Kernel capabilities.

Required specs:

- [run-lifecycle.md](run-lifecycle.md)
- [providers.md](providers.md)
- [prompts.md](prompts.md)
- [tool-calling.md](tool-calling.md)
- [approval-resume.md](approval-resume.md)
- [rag.md](rag.md)
- [memory.md](memory.md)
- [evals.md](evals.md)
- [observability.md](observability.md)
- [security-policy.md](security-policy.md)

Each spec should use this template:

```text
# Feature Spec: Name

## Goal
## Non-Goals
## User Stories
## Domain Model
## State Transitions
## API / CLI
## Failure Modes
## Security
## Observability
## Test Plan
```

Specs should be short enough to stay useful. They are design assumptions that evolve with implementation and eval results.
