# Rampart Agent — Multi-arch Docker Image
# Build:  docker build -t rampart-agent .
# Run:    docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... rampart-agent
# Multi:  docker buildx build --platform linux/amd64,linux/arm64 -t rampart-agent .

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="Rampart Agent"
LABEL org.opencontainers.image.description="Navigate Complexity with AI — Autonomous Agent Framework"
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash rampart

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn

COPY . .
RUN pip install --no-cache-dir -e . \
    && mkdir -p /home/rampart/.rampart/memory /home/rampart/.rampart/logs \
    && chown -R rampart:rampart /home/rampart/.rampart /app

USER rampart
ENV RAMPART_HOME=/home/rampart/.rampart
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:8000/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
