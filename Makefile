# ==============================================================================
# Crew Media Ops — Makefile
# ==============================================================================

.PHONY: help dev build up down test lint migrate clean logs shell

# Default: show help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --------------- Development ---------------

dev: ## Start development environment (SQLite + hot reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-d: ## Start development environment (detached)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

dev-pg: ## Start development with PostgreSQL
	docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile postgres up --build

# --------------- Production ---------------

build: ## Build production Docker images
	docker compose build

up: ## Start production environment
	docker compose up -d

down: ## Stop all services
	docker compose down

down-v: ## Stop all services and remove volumes
	docker compose down -v

restart: ## Restart all services
	docker compose restart

# --------------- Testing ---------------

test: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html -v

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	uv run pytest tests/integration/ -v

test-docker: ## Run tests inside Docker container
	docker compose exec backend python -m pytest --cov=src -v

# --------------- Linting & Type Checking ---------------

lint: ## Run ruff linter
	uv run ruff check src/ tests/

lint-fix: ## Run ruff with auto-fix
	uv run ruff check --fix src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

check: lint typecheck test ## Run all checks (lint + typecheck + test)

# --------------- Database Migrations ---------------

migrate: ## Run Alembic migrations (upgrade to head)
	uv run alembic upgrade head

migrate-docker: ## Run migrations inside Docker
	docker compose exec backend alembic upgrade head

migration: ## Create a new migration (usage: make migration MSG="add users table")
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Downgrade one migration
	uv run alembic downgrade -1

migrate-history: ## Show migration history
	uv run alembic history --verbose

# --------------- Utilities ---------------

logs: ## Tail logs from all services
	docker compose logs -f

logs-backend: ## Tail backend logs
	docker compose logs -f backend

shell: ## Open a shell in the backend container
	docker compose exec backend bash

psql: ## Connect to PostgreSQL
	docker compose exec db psql -U crew -d crew_media

clean: ## Remove caches, build artifacts, coverage reports
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml .coverage dist/ build/ *.egg-info

install: ## Install all dependencies (dev + browser)
	uv sync --all-extras
