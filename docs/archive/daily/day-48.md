# Day 48: Error Message and Troubleshooting Polish

## Goal

Improve first-user failure messages and troubleshooting guidance for Public
Alpha without adding new runtime capabilities.

## Scope

- Improve CLI API-unreachable messages.
- Cover JSON and file-upload API request paths.
- Add tests for actionable CLI connection failures.
- Expand troubleshooting docs for API, Workbench, and RAG search failure modes.
- Update Public Alpha milestone status.

## Tasks

- [x] Create Day 48 daily plan.
- [x] Add a shared CLI API-unreachable error message helper.
- [x] Use the helper for JSON API requests.
- [x] Use the helper for file-upload API requests.
- [x] Add CLI tests for actionable connection failure messages.
- [x] Expand troubleshooting docs.
- [x] Update milestone tracking.

## Acceptance

- [x] CLI API connection failures include the target URL.
- [x] CLI API connection failures tell users to start `agent-kernel-api`.
- [x] CLI API connection failures mention `AGENT_KERNEL_API_URL` or `--api-url`.
- [x] Troubleshooting covers CLI/API unreachable, Workbench unreachable, and
  empty RAG retrieval paths.
- [x] No new runtime feature scope is added.

## Verification

- [x] `git diff --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_cli_commands.py`

## Notes

- Day 48 does not add auth/RBAC, provider-native function calling, durable
  execution, real embeddings, object storage backends, or persisted evals.
