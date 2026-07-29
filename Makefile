.PHONY: setup test lint format typecheck cheap-eval verify web-lint web-build docker-config

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

web-lint:
	npm run lint

web-build:
	npm run build

docker-config:
	docker compose config

verify: lint typecheck test cheap-eval web-lint web-build docker-config
