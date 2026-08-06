.PHONY: setup test lint format typecheck cheap-eval release-eval release-smoke verify verify-web web-lint web-build web-e2e docker-config

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

release-smoke: release-eval docker-config
	uv run pytest tests/unit/test_api_health.py tests/unit/test_cli_commands.py tests/unit/test_worker_cli.py tests/unit/test_tools.py tests/unit/test_kb_search_tool.py tests/integration/test_api_run_lifecycle.py tests/integration/test_runtime_e2e.py tests/integration/test_api_approvals.py tests/integration/test_api_knowledge_base.py tests/integration/test_api_memory.py tests/integration/test_api_evals.py
	npm run lint
	npm run build

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
