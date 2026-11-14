.PHONY: setup test lint format typecheck cheap-eval release-eval release-smoke release-load-soak verify verify-web web-lint web-build web-e2e docker-config
.PHONY: docker-init docker-up docker-build docker-stop docker-down docker-status docker-logs docker-check
.PHONY: test-db-up test-db-down
.DEFAULT_GOAL := docker-init

AGENT_KERNEL_TEST_POSTGRES_PORT ?= 55432
export AGENT_KERNEL_TEST_POSTGRES_PORT
export AGENT_KERNEL_TEST_POSTGRES_URL ?= postgresql+psycopg://agent_kernel:test-only@127.0.0.1:$(AGENT_KERNEL_TEST_POSTGRES_PORT)/agent_kernel_test

test-db-up:
	docker compose -p agent-kernel-test -f deploy/test.compose.yml up --detach --wait

test-db-down:
	docker compose -p agent-kernel-test -f deploy/test.compose.yml down

docker-init:
	sh scripts/local-stack.sh init

docker-up:
	sh scripts/local-stack.sh up

docker-build:
	sh scripts/local-stack.sh build

docker-stop:
	sh scripts/local-stack.sh stop

docker-down:
	sh scripts/local-stack.sh down

docker-status:
	sh scripts/local-stack.sh ps

docker-logs:
	sh scripts/local-stack.sh logs $(SERVICE)

docker-check:
	sh scripts/local-stack.sh config

setup:
	uv sync
	npm install

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

cheap-eval:
	uv run agent-kernel eval report evals/rag-smoke.json

release-eval: cheap-eval
	uv run agent-kernel eval report evals/release-rag-gate.json
	uv run pytest tests/unit/test_tool_call_evals.py
	uv run pytest -q tests/integration/test_bounded_native_execution.py tests/integration/test_runtime_backoff.py tests/integration/test_native_continuation_wire.py tests/integration/test_execution_budget_edges.py
	uv run python scripts/timeline_regression.py

release-smoke: release-eval docker-config
	uv run pytest tests/unit/test_api_health.py tests/unit/test_cli_commands.py tests/unit/test_worker_cli.py tests/unit/test_tools.py tests/unit/test_kb_search_tool.py tests/integration/test_api_run_lifecycle.py tests/integration/test_runtime_e2e.py tests/integration/test_api_approvals.py tests/integration/test_api_knowledge_base.py tests/integration/test_api_memory.py tests/integration/test_api_evals.py
	npm run lint
	npm run build

release-load-soak:
	uv run python scripts/release_load_soak.py --profile quick

web-lint:
	npm run lint

web-build:
	npm run build

web-e2e:
	npm run test:e2e

docker-config:
	docker compose config

verify: lint typecheck test release-eval web-lint web-build docker-config

verify-web: web-lint web-build web-e2e
