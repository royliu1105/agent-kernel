# Day 46: Public Alpha Examples Refresh

## Goal

Make examples easier for an early external user to discover, copy, and run after
the Public Alpha live Web integrations.

## Scope

- Refresh examples README around current runtime paths.
- Add a guided Public Alpha walkthrough.
- Add a copyable HTTP request collection.
- Update Quickstart and Public Alpha guide links.
- Update Public Alpha milestone status.

## Tasks

- [x] Create Day 46 daily plan.
- [x] Refresh examples README.
- [x] Add Public Alpha walkthrough.
- [x] Add Public Alpha HTTP request collection.
- [x] Update Quickstart examples section and Workbench live-path notes.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] A new user can find a guided end-to-end examples path.
- [x] Examples cover agent run, RAG retrieval, memory, eval, and Web Workbench.
- [x] Workbench examples mention current live paths and fixture-backed
  remaining boundaries.
- [x] HTTP examples expose useful API calls without adding a new toolchain.

## Verification

- [x] `git diff --check`
- [x] `uv run ruff check .`
- [x] `npm run lint`

## Notes

- Day 46 does not add new runtime behavior.
- Day 46 does not add provider-native function calling, auth/RBAC, real
  embeddings, durable queues, or object storage backends.
