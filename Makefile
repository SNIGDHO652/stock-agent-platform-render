.PHONY: install dev test lint format typecheck up down migrate

install:
	python -m pip install -e ".[dev]"

dev:
	fastapi dev app/main.py


test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy app

up:
	docker compose up --build

down:
	docker compose down

migrate:
	alembic upgrade head
