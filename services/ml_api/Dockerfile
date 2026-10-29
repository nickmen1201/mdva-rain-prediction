# =============================================================================
# services/ml_api/Dockerfile — FastAPI ML Service (Python 3.11)
# =============================================================================
# Build context: raíz del repo (los modelos viven en models/, convención CCDS v2).
#   docker build -f services/ml_api/Dockerfile .
# El .dockerignore de la raíz solo deja entrar services/ml_api/ y models/.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Instalar curl (necesario para el healthcheck del compose)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias primero (cache de capas)
COPY services/ml_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código y los modelos entrenados
COPY services/ml_api/main.py .
COPY models/ models/
ENV MDVA_MODELS_DIR=/app/models

# Exponer el puerto del servicio ML
EXPOSE 8081

# Healthcheck interno
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8081/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8081} --workers 1 --limit-concurrency 10"]
