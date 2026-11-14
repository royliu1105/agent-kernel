# Repository Working Agreements

- Default local runtime startup is **Docker only**: `make docker-up` (or
  `sh scripts/local-stack.sh up`). API, Worker, Web, PostgreSQL, Redis and the
  observability services belong to the single `agent-kernel-local` Compose project.
- PostgreSQL is the only supported database. Use `make test-db-up` for the
  separate disposable test service and `AGENT_KERNEL_TEST_POSTGRES_URL` for tests.
  Never point tests/drills at the active Docker runtime DB; see
  `docs/postgresql-only.md`. Missing DATABASE_URL must not fall back to SQLite.
- Do not start host `uv run agent-kernel-api`, a Worker loop, `next dev` or
  `next start` unless the user explicitly requests a host-debug exception.
  Short-lived host lint/typecheck/unit-test tools remain allowed.
  Browser tests connect to Docker locally; only an explicit isolated CI/test
  harness may enable `PLAYWRIGHT_MANAGED_SERVER=1` for a temporary test server.
- Read `docs/docker-local.md` before operating the local stack. Use `stop` or
  `down` without volumes; never delete data or credentials without explicit approval.
- Legacy `.agent-kernel/local-experience`, its pre-Docker backup, and the older
  `.agent-kernel/agent_kernel.db` were deleted with explicit maintainer approval
  on 2026-11-14. No legacy SQLite rollback copy is retained at those paths.
  Do not recreate or restart the retired host runtime.
- Keep credentials in ignored private runtime files, never in chat, source, or logs.
  The default local profile uses mock models and Mailpit, not paid calls or real email.
- `resource/` is user-provided reference material, not the maintained runtime.
  Do not modify it or include it in build contexts unless explicitly requested.
