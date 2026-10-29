# =============================================================================
# services/ml_api/Dockerfile — FastAPI ML Service (Python 3.11)
# =============================================================================
# Build context: raíz del repo (modelos en models/ y paquete mdva/, convención CCDS v2).
#   docker build -f services/ml_api/Dockerfile .
# El .dockerignore de la raíz solo deja entrar lo que el servicio necesita. La imagen
# replica la estructura del repo para que la dependencia local `mdva = ../..` resuelva.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app/services/ml_api

# Instalar curl (necesario para el healthcheck del compose)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias exactas desde el lockfile (falla si uv.lock no corresponde a pyproject.toml)
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
COPY pyproject.toml README.md /app/
COPY mdva/ /app/mdva/
COPY services/ml_api/pyproject.toml services/ml_api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache
ENV PATH="/app/services/ml_api/.venv/bin:$PATH"

# Código del servicio y modelos (v1: *.pkl; v2: rain_classifier/)
COPY services/ml_api/main.py services/ml_api/v2.py services/ml_api/monitoring.py ./
COPY models/ /app/models/
ENV MDVA_MODELS_DIR=/app/models

# Exponer el puerto del servicio ML
EXPOSE 8081

# Healthcheck interno
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8081/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8081} --workers 1 --limit-concurrency 10"]
