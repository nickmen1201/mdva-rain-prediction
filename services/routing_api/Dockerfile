# =============================================================================
# services/routing_api/Dockerfile — FastAPI Routing Service
# =============================================================================
# Rutas sobre el grafo vial OSM del Valle de Aburrá (OSMnx + NetworkX) con tiempos por
# tipo de vía y la probabilidad de lluvia del modelo evaluado (ML API v2, ml-service).
#
# Puerto: 8000
# Nota: el primer arranque puede tardar varios minutos si descarga el grafo OSM.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias exactas desde el lockfile (falla si uv.lock no corresponde a pyproject.toml)
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

RUN mkdir -p /app/cache

EXPOSE 8000

# Variables de entorno para integración con MDVA
ENV MDVA_ML_URL=http://ml-service:8081
ENV GRAPH_CACHE_FILE=/app/cache/valle_aburra.graphml

HEALTHCHECK --interval=15s --timeout=10s --retries=8 --start-period=120s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 10"]
