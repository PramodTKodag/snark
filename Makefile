.PHONY: help up down build logs test test-cov format lint migrate makemigrations seed shell

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

shell: ## Django shell
	cd snark && python manage.py shell
