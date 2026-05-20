.PHONY: all setup install install-dev lint format test test-unit test-integration test-e2e coverage build run-dev docker-build clean

# Default target
all: install

# Setup development environment
setup:
	@echo "=== Setting up development environment ==="
	pip install -e .
	pip install -r requirements-dev.txt
	pre-commit install

# Install production dependencies
install:
	@echo "=== Installing production dependencies ==="
	pip install -e .

# Install development dependencies
install-dev:
	@echo "=== Installing development dependencies ==="
	pip install -e .
	pip install -r requirements-dev.txt

# Run linting
lint:
	@echo "=== Running linting ==="
	flake8 beijixing/ tests/
	mypy beijixing/
	bandit -r beijixing/ -f json -o bandit-report.json

# Format code
format:
	@echo "=== Formatting code ==="
	black beijixing/ tests/
	isort beijixing/ tests/

# Run all tests
test:
	@echo "=== Running all tests ==="
	pytest tests/

# Run unit tests
test-unit:
	@echo "=== Running unit tests ==="
	pytest tests/unit/

# Run integration tests
test-integration:
	@echo "=== Running integration tests ==="
	pytest tests/integration/

# Run e2e tests
test-e2e:
	@echo "=== Running e2e tests ==="
	pytest tests/e2e/

# Generate coverage report
coverage:
	@echo "=== Generating coverage report ==="
	pytest tests/ --cov=beijixing --cov-report=html --cov-report=term

# Build package
build:
	@echo "=== Building package ==="
	python -m build

# Run development server
run-dev:
	@echo "=== Starting development server ==="
	uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload

# Build Docker image
docker-build:
	@echo "=== Building Docker image ==="
	docker build -t beijixing:latest .

# Clean build artifacts
clean:
	@echo "=== Cleaning build artifacts ==="
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .mypy_cache/ htmlcov/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete