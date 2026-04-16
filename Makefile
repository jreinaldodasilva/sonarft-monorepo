PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

.PHONY: help setup dev build test lint clean install

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Create venv and install all dependencies (run once)
	python3 -m venv .venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e packages/bot
	$(PIP) install -r packages/api/requirements.txt
	cd packages/web && npm ci
	@echo ""
	@echo "✓ Environment ready. Activate with: source .venv/bin/activate"

# ── Installation ──────────────────────────────────────────────────────────────

install: install-bot install-api install-web ## Install all dependencies

install-bot: ## Install bot package dependencies
	$(PIP) install -e packages/bot

install-api: ## Install API package dependencies
	$(PIP) install -r packages/api/requirements.txt

install-web: ## Install web package dependencies
	cd packages/web && npm ci

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Start all services with Docker Compose (hot reload)
	docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up

dev-api: ## Start API server only (requires bot installed)
	cd packages/api && ../../.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

dev-web: ## Start web dev server only
	cd packages/web && npm run dev

dev-bot: ## Run bot engine directly (for testing)
	cd packages/bot && ../../.venv/bin/python -m sonarft_bot

# ── Build ─────────────────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker-compose -f infra/docker-compose.yml build

build-web: ## Build web production bundle
	cd packages/web && npm run build

# ── Testing ───────────────────────────────────────────────────────────────────

test: test-bot test-api test-web ## Run all tests

test-bot: ## Run bot package tests
	cd packages/bot && ../../.venv/bin/pytest

test-api: ## Run API package tests
	cd packages/api && ../../.venv/bin/pytest

test-web: ## Run web package tests
	cd packages/web && npm test

# ── Linting ───────────────────────────────────────────────────────────────────

lint: lint-bot lint-api lint-web ## Lint all packages

lint-bot: ## Lint bot package
	cd packages/bot && python -m pylint sonarft_*.py || true

lint-api: ## Lint API package
	cd packages/api && python -m pylint src/ || true

lint-web: ## Lint web package
	cd packages/web && npm run lint

# ── Utilities ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf packages/web/build packages/web/dist
	docker-compose -f infra/docker-compose.yml down --volumes 2>/dev/null || true

logs: ## Tail logs from all running services
	docker-compose -f infra/docker-compose.yml logs -f
