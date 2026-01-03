.PHONY: up down test migrate format delete-revision upgrade-pybinbot

ifneq (,$(wildcard ../.env))
    include ../.env
    export
endif

VENV=./.venv

cmd-exists-%:
	@hash $(*) > /dev/null 2>&1 || \
		(echo "ERROR: '$(*)' must be installed and available on your PATH."; exit 1)

up:  ## Run Docker Compose services
	docker compose up -f ../compose.yml --pull always -d --build

down:  ## Shutdown Docker Compose services
	docker compose down -f ../compose.yml --volumes --remove-orphans

test:  ## Run tests
	uv run pytest tests/ -v

dump-fixtures:  ## Dump test fixtures from database (requires DB to be running)
	uv run python tests/fixtures/dump_fixtures.py

migrate:  ## Apply latest alembic migrations
	uv run alembic upgrade head
	uv run alembic stamp head
	@if [ -n "$(m)" ]; then \
		uv run alembic revision --autogenerate -m "$(m)" --head head; \
	fi

migrate-reset:  ## downgrade and upgrade
	uv run alembic downgrade -1
	uv run alembic upgrade head

format: 
	ruff format .
	ruff check .  --fix
	mypy .

upgrade-pybinbot:  ## Upgrade pybinbot to latest compatible version
# --frozen force is to install because of scipy
	uv lock --upgrade-package pybinbot --frozen
	uv sync --extra dev

delete-revision:  ## Delete a specific Alembic revision from the database
	@if [ -z "$(revision)" ]; then \
		echo "ERROR: You must provide a revision. Usage: make delete-revision revision=<revision>"; \
		exit 1; \
	fi
	@echo "POSTGRES_PASSWORD: $(POSTGRES_PASSWORD)"
	@echo "Deleting revision $(revision) from alembic_version table..."
	docker exec -ti binbot_api_db sh -c "PGPASSWORD=$(POSTGRES_PASSWORD) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \"DELETE FROM alembic_version WHERE version_num = '$(revision)';\""
