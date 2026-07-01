.PHONY: help up down build logs test test-cov format lint migrate makemigrations seed shell \
	mcp-install mcp mcp-http mcp-inspect mcp-test \
	ensure-admin admin prune-logs update-pricing

# snark-mcp config. SNARK_API_URL defaults to the port snark runs on (WIT_PORT
# from .env, else 8100). Override on the command line, e.g.
#   make mcp-http SNARK_API_URL=http://localhost:9000 MCP_PORT=8001
WIT_PORT := $(shell grep -E '^WIT_PORT=' .env 2>/dev/null | cut -d= -f2)
WIT_PORT := $(if $(WIT_PORT),$(WIT_PORT),8100)
SNARK_API_URL ?= http://localhost:$(WIT_PORT)
MCP_PORT ?= 8000
DAYS ?= 90

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start dev server
	docker compose --profile dev up --build

down: ## Stop all containers
	docker compose --profile dev --profile prod down

build: ## Build Docker image
	docker compose build

logs: ## Tail container logs
	docker compose --profile dev logs -f

test: ## Run tests with pytest
	cd snark && python -m pytest -v

test-cov: ## Run tests with coverage
	cd snark && python -m pytest --cov=wit --cov-report=term-missing -v

format: ## Format code with black + isort
	cd snark && black . && isort .

lint: ## Run flake8 linter
	flake8 snark

migrate: ## Run Django migrations
	cd snark && python manage.py migrate

makemigrations: ## Generate Django migrations
	cd snark && python manage.py makemigrations wit

seed: ## Seed personas
	cd snark && python manage.py seed_personas

ensure-admin: ## Create/update admin superuser from ADMIN_* env vars
	cd snark && python manage.py ensure_admin

admin: ## Create an admin superuser interactively
	cd snark && python manage.py createsuperuser

prune-logs: ## Delete response logs older than DAYS (default 90)
	cd snark && python manage.py prune_logs --days $(DAYS)

update-pricing: ## Refresh wit/pricing_data.json from LiteLLM's model cost map
	cd snark && python manage.py update_pricing

shell: ## Django shell
	cd snark && python manage.py shell

# --- snark-mcp (MCP server) -------------------------------------------------
# Auto-creates the venv on first use of any mcp target.
mcp-server/.venv:
	cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

mcp-install: mcp-server/.venv ## Install snark-mcp into mcp-server/.venv

mcp: mcp-server/.venv ## Run snark-mcp over stdio (for MCP clients / Inspector)
	cd mcp-server && SNARK_API_URL=$(SNARK_API_URL) .venv/bin/snark-mcp

mcp-http: mcp-server/.venv ## Run snark-mcp over Streamable HTTP (MCP_PORT, default 8000)
	cd mcp-server && SNARK_API_URL=$(SNARK_API_URL) .venv/bin/snark-mcp --http --host 127.0.0.1 --port $(MCP_PORT)

mcp-inspect: mcp-server/.venv ## Run snark-mcp under the MCP Inspector
	cd mcp-server && SNARK_API_URL=$(SNARK_API_URL) npx @modelcontextprotocol/inspector .venv/bin/snark-mcp

mcp-test: mcp-server/.venv ## Run the snark-mcp test suite
	cd mcp-server && .venv/bin/pytest -v
