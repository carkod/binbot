.PHONY: up down test migrate format

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

VENV=./.venv

cmd-exists-%:
	@hash $(*) > /dev/null 2>&1 || \
		(echo "ERROR: '$(*)' must be installed and available on your PATH."; exit 1)

up:  ## Run Docker Compose services
	docker compose up --pull always -d --build 

down:  ## Shutdown Docker Compose services
	docker compose down --volumes --remove-orphans

test:  ## Run tests
	uv run pytest -v --tb=short --disable-warnings --maxfail=1

migrate:  ## Apply latest alembic migrations
	uv run alembic upgrade head
	uv run alembic revision --autogenerate -m "$(message)" --head head

format: 
	ruff format .
	ruff check .  --fix
	mypy .
