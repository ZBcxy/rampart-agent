.PHONY: all setup install test test-unit test-integration lint clean \
        docker-build docker-up docker-down docker-logs docker-push \
        run run-gateway run-mcp run-single-shot \
        init doctor config login sessions profiles

# ── Development ──────────────────────────────────────────────────────────
all: install

setup:
	python -m venv venv && venv/bin/pip install -r requirements.txt

install:
	pip install -e .

test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/unit/ -v

test-integration:
	python -m pytest tests/integration/ -v

lint:
	python -m flake8 core/ tools/ mcp/ protocols/ cli/ --max-line-length=120 --ignore=E501,W503

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache dist build *.egg-info htmlcov .coverage

# ── Run ──────────────────────────────────────────────────────────────────
run:
	python -m cli.rampart_cli

run-gateway:
	python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload

run-mcp:
	python -m mcp.server --stdio

run-single-shot:
	python -m cli.rampart_cli "$(PROMPT)"

# ── Lifecycle ────────────────────────────────────────────────────────────
init:
	python -m cli.rampart_cli init

doctor:
	python -m cli.rampart_cli doctor

config:
	python -m cli.rampart_cli config

login:
	python -m cli.rampart_cli login

sessions:
	python -m cli.rampart_cli sessions list

profiles:
	python -m cli.rampart_cli profiles list

update:
	python -m cli.rampart_cli update

logo:
	python -m cli.rampart_cli --logo

logo-minimal:
	python -m cli.rampart_cli --logo --style minimal

logo-box:
	python -m cli.rampart_cli --logo --style box

# ── Install lifecycle ────────────────────────────────────────────────────
install-full:
	python install.py

install-quiet:
	python install.py --no-launch

upgrade:
	python install.py --upgrade

uninstall:
	python install.py --uninstall

uninstall-keep:
	python install.py --uninstall --keep-data

verify:
	python install.py --verify

doctor-install:
	python install.py --doctor

# ── Docker ───────────────────────────────────────────────────────────────
DOCKER_IMAGE ?= rampart-agent
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
	docker compose logs -f rampart

docker-shell:
	docker compose exec rampart bash

docker-push:
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
