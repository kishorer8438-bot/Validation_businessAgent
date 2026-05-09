# RAG Validation System - Development Makefile

.PHONY: help install install-dev test test-verbose test-coverage lint format clean build docs serve api help

# Default target
help: ## Show this help message
	@echo "RAG Validation System - Development Commands"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Testing
test: ## Run all tests
	pytest

test-verbose: ## Run tests with verbose output
	pytest -v

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-integration: ## Run integration tests only
	pytest -m integration

test-unit: ## Run unit tests only
	pytest -m unit

# Code Quality
lint: ## Run linting checks
	flake8 src tests scripts
	mypy src

format: ## Format code with black and isort
	black src tests scripts
	isort src tests scripts

format-check: ## Check code formatting without making changes
	black --check --diff src tests scripts
	isort --check-only --diff src tests scripts

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# Cleaning
clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete

clean-logs: ## Clean log files
	find logs -type f -name "*.log" -delete

clean-outputs: ## Clean output files
	find outputs -type f -delete

clean-all: clean clean-logs clean-outputs ## Clean everything

# Building
build: ## Build the package
	python -m build

build-wheel: ## Build wheel distribution
	python -m build --wheel

build-sdist: ## Build source distribution
	python -m build --sdist

# Docker
docker-build: ## Build Docker image
	docker build -t rag-validation-system .

docker-run: ## Run Docker container
	docker run -p 8000:8000 rag-validation-system

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

# API Server
serve: ## Start the FastAPI server
	uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

api: serve ## Alias for serve

# Documentation
docs: ## Build documentation
	sphinx-build docs docs/_build/html

docs-serve: ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8080

# Development
dev-setup: install-dev pre-commit-install ## Set up development environment
	@echo "Development environment setup complete!"

dev-update: ## Update all dependencies
	pip install --upgrade -r requirements.txt
	pip install --upgrade -e ".[dev]"

# CI/CD
ci-test: ## Run tests for CI
	pytest --cov=src --cov-report=xml --junitxml=junit.xml

ci-lint: ## Run linting for CI
	flake8 src tests scripts --output-file=flake8.txt
	mypy src --xml-report=mypy.xml

# Utility
count-lines: ## Count lines of code
	find src tests scripts -name "*.py" -exec wc -l {} + | tail -1

deps-update: ## Update dependencies to latest versions
	pip install --upgrade pip-tools
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements-dev.in

# Quick commands
run: ## Quick run with sample file
	python -m src.main data/raw/sample.txt

validate: ## Validate sample payload
	python -m src.main data/payload.json --payload-file

ai-help: ## Run AI helper with sample error
	python scripts/ai_helper.py "Amount must be > 0"