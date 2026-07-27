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
- What minimal `Run` fields must be persisted on Day 2?
- Should IDs be UUIDs at the database layer from the start?
- Should API request/response schemas reuse domain models or have separate DTOs?
- How should `RunEvent` be represented for timeline reconstruction?
- What is the first migration naming convention?

## Tasks

- [ ] Check current git status.
- [ ] Read `docs/specs/run-lifecycle.md`.
- [ ] Refine `docs/specs/run-lifecycle.md` if implementation semantics become clearer.
- [ ] Add storage dependencies: SQLAlchemy, Alembic, psycopg.
- [ ] Add database settings/config surface.
- [ ] Add SQLAlchemy declarative base and session factory.
- [ ] Add Alembic configuration.
- [ ] Create initial migration for core execution tables.
- [ ] Add storage models for `Agent`, `Run`, `RunStep`, and `RunEvent`.
- [ ] Add repository methods for creating and reading agents.
- [ ] Add repository methods for creating and reading runs.
- [ ] Add minimal API schemas for agent/run create/read.
- [ ] Add `POST /v1/agents`.
- [ ] Add `GET /v1/agents/{agent_id}`.
- [ ] Add `POST /v1/agents/{agent_id}/runs`.
- [ ] Add `GET /v1/runs/{run_id}`.
- [ ] Add `GET /v1/runs/{run_id}/events`.
- [ ] Add unit tests for state defaults and transition guard helpers if introduced.
- [ ] Add integration tests for API create/read flow.
- [ ] Update `docs/milestones.md` Phase 1 progress.

## Acceptance

- [ ] Database migration can be generated/applied against local Postgres.
- [ ] Agent can be created through API.
- [ ] Agent can be fetched through API.
- [ ] Run can be created for an agent through API.
- [ ] Run can be fetched through API.
- [ ] Run events endpoint returns an empty or initial timeline.
- [ ] Tests cover the create agent -> create run -> inspect run path.
- [ ] Phase 1 checklist is updated for completed items.

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
