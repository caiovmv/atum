# Imagem base para API e Runner (mesmo código, comandos diferentes)
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/
RUN pip install --no-cache-dir -e .
# API: CMD em docker-compose
# Runner: command override em docker-compose
