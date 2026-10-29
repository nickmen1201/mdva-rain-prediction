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

### v2 (modelo `rain_classifier`, contrato en `specs/006-ml-api-v2/contracts/openapi-v2.yaml`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v2/health` | Estado y versión del modelo cargado |
| POST | `/v2/predict` | Probabilidad y nivel de alerta para un punto y una hora (`time_utc` + 9 variables del pronóstico) |
| POST | `/v2/predict/batch` | Hasta 200 registros en una llamada (grilla del heatmap, pronóstico horario) |
| POST | `/v2/monitor/trip` | Nivel de cambio durante un viaje (reglas RF-17) |

Errores en Problem Details (RFC 7807, `application/problem+json`). El modelo se carga al arrancar; si no es compatible con el entorno (versión de scikit-learn o contrato de features), el servicio no arranca.

### v1 (modelos heredados; se retiran en la spec 007)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado y modelos cargados |
| POST | `/predecir/{modelo}` | `random_forest` o `regresion_logistica` |
| POST | `/predecir/ambos` | Ambos modelos en una llamada |
| POST | `/monitorear/trayecto` | Cambio de condiciones durante un viaje |

Documentación interactiva: http://localhost:8081/docs
