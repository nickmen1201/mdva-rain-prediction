# ML API — predicción de lluvia

Servicio FastAPI que sirve los modelos de `models/` (raíz del repo).

## Ejecutar

```bash
# Con el stack completo (recomendado)
docker compose -f docker-compose.dev.yml up --build ml-service

# Local, desde la raíz del repo
uv sync --project services/ml_api
uv run --project services/ml_api uvicorn main:app --app-dir services/ml_api --port 8081
```

La carpeta de modelos se toma de `MDVA_MODELS_DIR` (en el contenedor: `/app/models`); si no está definida, usa `models/` en la raíz del repo.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado y modelos cargados |
| POST | `/predecir/{modelo}` | `random_forest` o `regresion_logistica` |
| POST | `/predecir/ambos` | Ambos modelos en una llamada (lo usa el Backend) |
| POST | `/monitorear/trayecto` | Cambio de condiciones durante un viaje |

Documentación interactiva: http://localhost:8081/docs
