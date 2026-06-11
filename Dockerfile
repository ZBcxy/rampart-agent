# ── Polaris Agent — Multi-arch Docker Image ─────────────────────────────
# Build: docker build -t polaris-agent .
# Run:   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... polaris-agent
#
# Multi-arch build:
#   docker buildx build --platform linux/amd64,linux/arm64 -t polaris-agent .

# ── Stage 1: Build dependencies ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies separately for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install uvicorn[standard] gunicorn

# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="Polaris Agent"
LABEL org.opencontainers.image.description="Autonomous Multi-Agent Framework — OODA + DAG + Blackboard"
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash polaris

# Copy installed deps
COPY --from=builder /install /usr/local

# Copy application
WORKDIR /app
COPY --chown=polaris:polaris . .

# Create data directories
RUN mkdir -p /home/polaris/.polaris/memory /home/polaris/.polaris/logs \
    && chown -R polaris:polaris /home/polaris/.polaris

USER polaris
ENV POLARIS_HOME=/home/polaris/.polaris
ENV PYTHONUNBUFFERED=1

EXPOSE 8000 9000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:8000/v1/health || exit 1

# Default: run gateway server
CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
