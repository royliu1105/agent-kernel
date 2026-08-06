.PHONY: setup test lint format typecheck cheap-eval release-eval verify verify-web web-lint web-build web-e2e docker-config

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
