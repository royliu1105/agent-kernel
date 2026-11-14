# Quickstart

The default local runtime is **Docker only**. API, Worker, Web, PostgreSQL,
Redis and all observability services run together, with mock models and a local
Mailpit mailbox. No external model or SMTP credentials are required.

## Start

Install/start Docker Desktop (or Docker Engine with Compose), then run from the
repository root:

```bash
make docker-up
make docker-status
```

Without make: `sh scripts/local-stack.sh up`. The wrapper also uses POSIX `sh`
and `openssl`; host Python/Node are not required to run the services.

Open the Web at `http://127.0.0.1:3000`, API docs at
`http://127.0.0.1:8000/docs`, Grafana at `http://127.0.0.1:3090` and the local
test inbox at `http://127.0.0.1:8025`. Grafana username is `admin`; its password
is generated in `.agent-kernel/docker-local/grafana-password` (do not commit it).

All published ports are loopback-only. The default API is unauthenticated and
intended for a trusted local machine, not public hosting. PostgreSQL/Redis are
internal-only. See [Docker operations](docker-local.md) for all 13 services,
configuration, data/backup boundaries and remaining acceptance gates.

## Run an Agent

The API applies migrations automatically. The Worker runs continuously.
Execute CLI commands inside the API container so they share its database:

```bash
sh scripts/local-stack.sh exec -T api agent-kernel agent create --name "Local Test Agent"
sh scripts/local-stack.sh exec -T api agent-kernel run create <agent-id> --input '{"task":"hello runtime","model":"mock:echo"}'
sh scripts/local-stack.sh exec -T api agent-kernel run queue <run-id>
sh scripts/local-stack.sh exec -T api agent-kernel run inspect <run-id>
sh scripts/local-stack.sh exec -T api agent-kernel run events <run-id>
```

Use the returned IDs in subsequent commands. Expected final status: `succeeded`.
The Web's live run lookup accepts that run ID. Some other Workbench sections
remain fixture-backed previews; starting Docker does not change their scope.
Do not start a host API, Worker loop or Next server alongside this stack.

## RAG and Evals

```bash
sh scripts/local-stack.sh exec -T api agent-kernel kb create --name "Engineering Handbook"
sh scripts/local-stack.sh exec -T api agent-kernel document upload <knowledge-base-id> /app/README.md
sh scripts/local-stack.sh exec -T api agent-kernel document ingest <document-id>
sh scripts/local-stack.sh exec -T api agent-kernel document chunk <document-id>
sh scripts/local-stack.sh exec -T api agent-kernel document index <document-id>
sh scripts/local-stack.sh exec -T api agent-kernel kb search <knowledge-base-id> --query "Agent Kernel"
sh scripts/local-stack.sh exec -T api agent-kernel eval report evals/rag-smoke.json
```

These paths use deterministic mock embeddings. Objects live in a named volume,
not S3; pgvector is enabled by PostgreSQL migrations. Provider activation is a
separate, explicit step. Do not place real keys in browser `NEXT_PUBLIC_*` values.

## Daily Commands

```bash
make docker-logs SERVICE=worker
make docker-stop
make docker-up
make docker-down
```

Both `stop` and `down` preserve data volumes. The default wrapper does not offer
volume deletion. `docker-up` rebuilds changed code; there is no host hot reload.
Bare `docker compose up` is the lower-level base template, not this full default.

Host lint/typecheck/tests remain available with the contributor toolchain in
[development environment](development-environment.md). Test the running Docker
Web without starting a host server:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 AGENT_KERNEL_TEST_DOCKER_WEB=1 npm run test:e2e
```

For troubleshooting, include the failing command and redacted service logs,
never passwords, API keys, private documents or raw task content. See
[troubleshooting](troubleshooting.md), [Docker operations](docker-local.md), and
[observability backends](observability-backends.md).
