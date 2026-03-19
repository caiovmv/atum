# Imagem base para API e Runner (mesmo código, comandos diferentes)
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev ffmpeg procps util-linux \
    && rm -rf /var/lib/apt/lists/*

# 1) Copiar apenas metadados de dependências e instalar (cache de deps)
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -e . || true

# 2) Copiar código-fonte (invalida só a partir daqui)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docker/entrypoint-api.sh ./docker/entrypoint-api.sh
RUN chmod +x ./docker/entrypoint-api.sh && sed -i 's/\r$//' ./docker/entrypoint-api.sh
RUN pip install --no-cache-dir -e . py-spy

RUN addgroup --system atum && adduser --system --ingroup atum atum \
    && chown -R atum:atum /app
USER atum
