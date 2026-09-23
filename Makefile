SHELL := /bin/bash

bootstrap:
	@test -f .env || cp .env.example .env
	@echo "Configuration ready."

dev: bootstrap
	docker compose up --build

stop:
	docker compose down

lint:
	ruff check .
	cd apps/web && npm run lint

typecheck:
	mypy apps services packages
	cd apps/web && npm run typecheck

test:
	pytest -q tests/unit tests/contract

test-integration:
	pytest -q tests/integration

test-e2e:
	pytest -q tests/e2e

test-security:
	pytest -q tests/adversarial

benchmark:
	python scripts/benchmark.py

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

docs:
	python scripts/build_docs.py

