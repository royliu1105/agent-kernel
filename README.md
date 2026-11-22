# Agent Kernel

Self-hosted, auditable, resumable **single-agent** runtime for internal assistant
apps: tools, policy, human approval, memory, knowledge bases, evals, and
observability.

It is a task-oriented execution platform (API + Worker + CLI + Web Workbench)—
not a chat-only wrapper and not a public multi-tenant SaaS. Isolation uses
**Workspace** scoping and RBAC; that is not certified public-tenant isolation.
Production readiness is a scoped acceptance goal, not something implied by the
release number alone.

## Problem

Teams need an agent that can call tools safely, pause for approval, resume after
interrupts, ground answers in team documents, and leave an auditable trail. Most
“agent demos” skip durable execution, policy, and workspace scoping. Agent Kernel
is the control plane and worker for that bounded job—not a multi-agent studio.

## Architecture (sketch)

```text
Web Workbench / CLI
        |
        v
FastAPI  — identity, Workspace, Agent, Run, knowledge, approvals
        |
        +--> PostgreSQL / pgvector   (state, checkpoints, vectors)
        +--> Redis                   (queue hints, rate limits)
        +--> Object store            (documents)
        |
        v
Worker --> Runtime --> Provider / Tools / Policy / Memory / RAG
                         |
                         v
                   events, usage, logs, traces, evals
```

Default local stack is **Docker only** (`make docker-up`): API, Worker, Web,
PostgreSQL, Redis, and observability services in one Compose project. Details:
[project overview](docs/project-overview.md), [architecture](docs/architecture.md).

## Quickstart (Docker only)

```bash
make docker-up
make docker-status
```

| Surface | URL |
| --- | --- |
| Web Workbench | http://127.0.0.1:3000 |
| API docs | http://127.0.0.1:8000/docs |
| Grafana | http://127.0.0.1:3090 |
| Mailpit (local mail) | http://127.0.0.1:8025 |

Default profile uses **mock models** and Mailpit—no paid provider or real SMTP.
Auth is off on this trusted localhost profile; do not expose it publicly. Ops,
data, and credentials: [Docker local](docs/docker-local.md). First-run commands:
[Quickstart](docs/quickstart.md). Fresh-clone rehearsal intent:
[clean-machine rehearsal](docs/clean-machine-rehearsal.md).

```bash
make docker-stop    # or make docker-down (keeps volumes)
```

Do not start host `api` / Worker / `next` alongside this stack.

## Limits (read before claiming features)

- Single-agent bounded execution; no general multi-agent DAG in the maintained runtime.
- Default `make docker-up` uses **mock models** and local Mailpit—not paid providers.
- Workspace ≠ finished public multi-tenant SaaS / SSO / DB-hard isolation.
- Deferred/conditional items (streaming chat journey, hybrid BM25/Rerank, advanced
  memory lifecycle, multi-agent) are listed in
  [reference follow-up](docs/reference-follow-up-plan.md) as **CF3–CF8**, not as
  current delivery.
- Memory injection limits and resume boundaries:
  [memory context safety](docs/specs/memory-context-safety.md).

## Doc map

| Need | Doc |
| --- | --- |
| Positioning, architecture, evidence vs limits | [Project overview](docs/project-overview.md) |
| Full current vs archive map | [docs/README.md](docs/README.md) |
| Run / operate locally | [Quickstart](docs/quickstart.md), [Docker operations](docs/docker-local.md) |
| Stuck on setup | [Troubleshooting](docs/troubleshooting.md) |
| Security limits | [SECURITY.md](SECURITY.md), [Auth and RBAC](docs/auth-rbac.md) |
| How to contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Pilot status ledger | [Real-scenario pilot](docs/real-scenario-pilot-plan.md), [pilot learning](docs/pilot-learning-guide.md) |

## Current release and development

Current release:

- [Agent Kernel v1.0.0](https://github.com/royliu1105/agent-kernel/releases/tag/v1.0.0), published 2026-08-07.

Current development:

- `master` contains **unreleased changes** beyond the `v1.0.0` tag. Historical
  release CI does not verify those changes; implementation CI and pilot
  acceptance are separate evidence.
- Status and evidence: [project overview](docs/project-overview.md).
- Pilot ledger: [real-scenario acceptance and controlled pilot](docs/real-scenario-pilot-plan.md)
  (PV1 technical prep finalized; bounded PV2 offline checks exist; CF1 disposition
  still open for full PV2; formal PV3 cohort and later gates tracked in that ledger).
- Observability ledger: [observability completion](docs/observability-completion-plan.md)
  (O1–O5). External email delivery needs inbox evidence, not only Mailpit.
- Completed [post-v1.0 capability hardening](docs/capability-hardening-plan.md)
  retains implementation evidence and explicit limits.
- Follow-ups: [reference follow-up plan](docs/reference-follow-up-plan.md)
  (CF1/CF2 pilot-entry; CF3–CF8 deferred/conditional).
- Separately authorized [local paid walkthrough](docs/local-paid-experience.md)
  is not full pilot or independent-user acceptance. The local paid profile and
  hash guard are a separate implementation follow-up to documentation commit
  `17af7db`; only their own submitted-revision CI can verify them, not older CI.
- Review the [upgrade and migration policy](docs/upgrade-migration-policy.md)
  before upgrading an existing deployment.

Historical delivery:

- [Public Alpha, Beta, and v1.0 plan](docs/post-v0.1-plan.md)
- [v1.0.0 release notes](docs/releases/v1.0.0.md)
- [Public Alpha summary](docs/archive/public-alpha-summary.md)
- [Feedback templates](.github/ISSUE_TEMPLATE)

Project shape:

```text
Python API + CLI + worker + PostgreSQL/pgvector storage + RAG/memory/tools/evals + Next.js Workbench
```

## Contributor toolchain

Required tools: Python 3.12 (`uv`), Node.js 24+, Docker Desktop, `direnv`,
`pre-commit`. Full workflow: [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
uv sync
npm install
uv run ruff check .
uv run mypy .
make test-db-up
make test
make test-db-down
npm run lint && npm run build
make verify
```

PostgreSQL is required for database tests; there is no SQLite fallback. The test
service is disposable and **must not** point at the live Docker runtime DB. See
[PostgreSQL-only storage and testing](docs/postgresql-only.md).

CLI against the running stack:

```bash
sh scripts/local-stack.sh exec -T api agent-kernel --version
```

## Feedback

Use GitHub Issues for reproducible bugs, focused feature requests, or first-run
feedback. Redact secrets, API keys, tokens, private documents, and private logs
before sharing output. Security reports: [SECURITY.md](SECURITY.md).
