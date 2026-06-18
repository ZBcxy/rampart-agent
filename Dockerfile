# Polaris Agent — Multi-arch Docker Image
# Build:  docker build -t polaris-agent .
# Run:    docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... polaris-agent
# Multi:  docker buildx build --platform linux/amd64,linux/arm64 -t polaris-agent .

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="Polaris Agent"
LABEL org.opencontainers.image.description="Navigate Complexity with AI — Autonomous Agent Framework"
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash polaris

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn

COPY . .
RUN pip install --no-cache-dir -e . \
    && mkdir -p /home/polaris/.polaris/memory /home/polaris/.polaris/logs \
    && chown -R polaris:polaris /home/polaris/.polaris /app

USER polaris
ENV POLARIS_HOME=/home/polaris/.polaris
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:8000/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
