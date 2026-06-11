.PHONY: all setup install test test-unit test-integration lint clean \
        docker-build docker-up docker-down docker-logs docker-push \
        run run-gateway run-mcp

# ── Development ──────────────────────────────────────────────────────────
all: install

setup:
	python -m venv venv && venv/bin/pip install -r requirements.txt -r requirements-dev.txt

install:
	pip install -e .

test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/unit/ -v

test-integration:
	python -m pytest tests/integration/ -v

lint:
	python -m flake8 core/ tools/ mcp/ protocols/ --max-line-length=120 --ignore=E501,W503

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache dist build *.egg-info

# ── Run ──────────────────────────────────────────────────────────────────
run:
	python -m cli.polaris_cli

run-gateway:
	python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload

run-mcp:
	python -m mcp.server --stdio

# ── Docker ───────────────────────────────────────────────────────────────
DOCKER_IMAGE ?= polaris-agent
DOCKER_TAG ?= latest

docker-build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-build-multi:
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) --push .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f polaris

docker-shell:
	docker compose exec polaris bash

docker-push:
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
