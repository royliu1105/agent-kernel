# Feature Spec: Prompt Versioning

## Goal

Provide an immutable prompt version baseline so agent behavior can be tied to explicit prompt
content before database-backed prompt management exists.

## Non-Goals

- Prompt CMS.
- Prompt editing UI.
- Prompt migrations or Postgres persistence.
- Prompt experiment tracking.
- Prompt eval comparison reports.

## User Stories

- As a runtime developer, I can register a prompt version and retrieve it by name/version.
- As an evaluator, I can refer to a stable prompt version in a deterministic test.
- As a maintainer, I can later replace the registry backend without changing prompt identity.

## Domain Model

Day 5 prompt types:

- `PromptVersion`
- `PromptRegistry`

`PromptVersion` is immutable and includes:

- `id`
- `name`
- `version`
- `content`
- `metadata`
- `created_at`

## State Transitions

Prompt versions are immutable. Registering the same name/version twice is rejected.

## API / CLI

No prompt API or CLI is exposed in Day 5.

## Failure Modes

- Duplicate prompt version registration.
- Missing prompt name/version.

## Security

Prompt content should not include secrets. The registry is in-memory for Day 5.

## Observability

Future run events should include prompt identity when prompt-backed execution is introduced.

## Test Plan

- Register prompt versions.
- Retrieve prompt by name/version.
- Retrieve latest prompt by name.
- Reject duplicate name/version.
