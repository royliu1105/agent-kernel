# Day 62: Durable Retry Visibility and Worker Restart Tests

## Goal

Harden durable execution confidence by proving retry/fallback visibility
survives session boundaries and worker restart recovery does not duplicate
expired in-flight work.

## Scope

- Add provider retry visibility regression coverage after database session
  reopen.
- Add safe tool retry visibility regression coverage after database session
  reopen.
- Add worker restart recovery coverage for expired running leases.
- Verify restarted workers do not re-execute failed stuck runs.
- Update durable execution docs and milestone progress.

## Tasks

- [x] Add durable provider retry event visibility test.
- [x] Add durable tool retry event visibility test.
- [x] Add worker restart recovery regression test.
- [x] Update daily plan and milestone progress.
- [x] Update run lifecycle and production docs.

## Acceptance

- [x] Provider retry events remain inspectable after reopening a database
  session.
- [x] Safe tool retry events remain inspectable after reopening a database
  session.
- [x] Expired running worker leases can be recovered after a simulated worker
  restart.
- [x] A restarted worker does not reprocess the failed stuck run.
- [x] Normal worker execution tests still pass.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_runtime_execution.py tests/unit/test_stuck_run_recovery.py`
- [x] `uv run pytest tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`

## Notes

- Day 62 does not add a public retry API.
- Day 62 does not add delayed retry scheduling or exponential backoff.
- Day 62 does not switch worker polling to Redis.
- Day 62 intentionally preserves the conservative recovery policy from Day 60:
  expired in-flight work fails rather than being blindly requeued.
