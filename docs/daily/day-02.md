# Day 02: Run Lifecycle and Storage Foundation

## Goal

Start Phase 1 by turning the Day 1 domain model skeleton into the first real persisted Agent run lifecycle foundation.

Day 2 should establish the data and service path for:

```text
create agent -> create run -> inspect run -> inspect run events
```

This is not the full agent execution loop yet. The focus is storage, API shape, and state semantics.

## Scope

Day 2 should cover:

- Phase 1 planning alignment.
- Run lifecycle spec refinement.
- Storage package dependencies.
- SQLAlchemy base setup.
- Alembic setup.
- Initial database models for Agent, Run, RunStep, and RunEvent.
- Repository interfaces/implementations for Agent and Run.
- API endpoints for creating and reading agents/runs.
- Tests for repository and API behavior.

Day 2 should not cover:

- OpenAI provider.
- Mock provider.
- Tool calling.
- Approval/resume.
- RAG.
- Memory.
- Full worker execution loop.
- Web UI changes beyond incidental type/build fixes.

## Design Questions

Resolve or explicitly defer these before implementation goes too far:

- What minimal `Agent` fields must be persisted on Day 2?
  - Resolved: identity, name, description, status, policy references, policy JSON, metadata,
    created timestamp.
- What minimal `Run` fields must be persisted on Day 2?
  - Resolved: identity, agent reference, status, input/output payloads, trace/error fields,
    token/cost totals, start/end/create timestamps.
- Should IDs be UUIDs at the database layer from the start?
  - Resolved: domain/API use UUIDs; database stores 36-character strings for initial
    SQLite/Postgres portability.
- Should API request/response schemas reuse domain models or have separate DTOs?
  - Resolved: separate HTTP DTOs in `agent_kernel_api.schemas`.
- How should `RunEvent` be represented for timeline reconstruction?
  - Resolved: append-only per-run timeline with monotonic `sequence` and JSON payload.
- What is the first migration naming convention?
  - Resolved: `0001_create_execution_tables`.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/run-lifecycle.md`.
- [x] Refine `docs/specs/run-lifecycle.md` if implementation semantics become clearer.
- [x] Add storage dependencies: SQLAlchemy, Alembic, psycopg.
- [x] Add database settings/config surface.
- [x] Add SQLAlchemy declarative base and session factory.
- [x] Add Alembic configuration.
- [x] Create initial migration for core execution tables.
- [x] Add storage models for `Agent`, `Run`, `RunStep`, and `RunEvent`.
- [x] Add repository methods for creating and reading agents.
- [x] Add repository methods for creating and reading runs.
- [x] Add minimal API schemas for agent/run create/read.
- [x] Add `POST /v1/agents`.
- [x] Add `GET /v1/agents/{agent_id}`.
- [x] Add `POST /v1/agents/{agent_id}/runs`.
- [x] Add `GET /v1/runs/{run_id}`.
- [x] Add `GET /v1/runs/{run_id}/events`.
- [x] Add unit tests for state defaults and transition guard helpers if introduced.
- [x] Add integration tests for API create/read flow.
- [x] Update `docs/milestones.md` Phase 1 progress.

## Acceptance

- [x] Database migration can be generated/applied against local Postgres.
- [x] Agent can be created through API.
- [x] Agent can be fetched through API.
- [x] Run can be created for an agent through API.
- [x] Run can be fetched through API.
- [x] Run events endpoint returns an empty or initial timeline.
- [x] Tests cover the create agent -> create run -> inspect run path.
- [x] Phase 1 checklist is updated for completed items.

## Verification

Run the available checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
docker compose ps
docker compose config
```

If database integration tests require Postgres:

```bash
docker compose up -d postgres redis
```

If API smoke testing is useful:

```bash
uv run uvicorn agent_kernel_api.main:app --reload
curl http://127.0.0.1:8000/healthz
```

## Notes

- Keep Day 2 focused on persistence and API shape.
- Do not start the full agent loop until the run state is stored and inspectable.
- Prefer small repository/service seams over endpoint-local database logic.
- The existing Docker containers may already be running from Day 1.

## Completion Notes

- Implemented `Agent`, `Run`, `RunStep`, and `RunEvent` storage models.
- Added Alembic migration `0001_create_execution_tables`.
- Added repository methods for creating/loading agents, creating/loading runs, and listing run events.
- Added HTTP DTOs and Day 2 API endpoints.
- Verified migration against local SQLite and Docker Postgres.
- Verification passed:
  - `uv sync`
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `uv run alembic upgrade head`
  - `DATABASE_URL=postgresql+psycopg://... uv run alembic upgrade head`
  - `docker compose ps`
  - `docker compose config`

Known caveat:

- FastAPI `TestClient` currently emits a Starlette deprecation warning about `httpx`.
  Tests pass; this should be revisited when the dependency ecosystem settles.
