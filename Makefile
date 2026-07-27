.PHONY: setup test lint format typecheck verify web-lint web-build docker-config

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

web-lint:
	npm run lint

web-build:
	npm run build

docker-config:
	docker compose config

verify: lint typecheck test web-lint web-build docker-config
