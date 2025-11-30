.PHONY: help install dev-install test lint format clean build-index run docker-build docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black ruff

test: ## Run tests
	pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=rag --cov=api --cov-report=html --cov-report=term

lint: ## Run linters
	python3 -m ruff check .

format: ## Format code
	python3 -m black .
	python3 -m ruff check . --fix

clean: ## Clean build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

build-index: ## Build the FAISS index
	python scripts/build_index.py

run: ## Run the API server
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Run the API server in production mode
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1

docker-build: ## Build Docker image
	docker build -t agendaflow:latest .

docker-run: ## Run Docker container
	docker run -d \
		-p 8000:8000 \
		-v $(PWD)/data:/app/data \
		--env-file .env \
		--name agendaflow \
		agendaflow:latest

docker-stop: ## Stop Docker container
	docker stop agendaflow || true
	docker rm agendaflow || true

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

setup-env: ## Copy .env.example to .env
	cp .env.example .env
	@echo "Don't forget to edit .env with your API keys!"
