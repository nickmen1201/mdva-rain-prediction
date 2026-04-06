# =============================================================================
# Data-science/Dockerfile — FastAPI ML Service (Python 3.11)
# =============================================================================
# Asume la siguiente estructura en la carpeta Data-science/:
#   main.py           ← entrypoint de FastAPI
#   requirements.txt  ← dependencias Python
#   models/
#     random_forest.pkl
#     regresion_logistica.pkl
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Instalar curl (necesario para el healthcheck del compose)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias primero (cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código y los modelos entrenados
COPY main.py .
COPY models/ models/

# Exponer el puerto del servicio ML
EXPOSE 8081

# Healthcheck interno
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8081/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
