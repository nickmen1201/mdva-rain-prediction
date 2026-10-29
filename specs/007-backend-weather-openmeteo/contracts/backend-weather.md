# Contract: clima en el Backend

## Dependencias externas (consumidas)

| Servicio | Llamada | Notas |
|---|---|---|
| Open-Meteo Forecast | `GET https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,cloud_cover,wind_speed_10m,wind_direction_10m,pressure_msl,precipitation,cape&forecast_days=2&timezone=GMT&wind_speed_unit=ms&temperature_unit=celsius&precipitation_unit=mm` | Una ubicación → objeto; varias → arreglo. Unidades verificadas. |
| ML API v2 | `POST /v2/predict/batch`, `POST /v2/monitor/trip` | Contrato: `specs/006-ml-api-v2/contracts/openapi-v2.yaml` |

## Endpoints del Backend (sin cambios de ruta)

| Endpoint | Cambio |
|---|---|
| `GET /api/weather/current` | **Aditivo**: `RainPredictionDTO.timestampDatoUtc` (instante UTC de la hora usada). `probabilidadRl` pasa a `null` (el modelo v2 no la entrega). `probabilidadRf` conserva el nombre por compatibilidad y contiene la probabilidad del modelo v2. |
| `GET /api/weather/forecast` | Sin cambios de forma; `timestamp` en UTC y `hora` en hora local de Bogotá. |
| `POST /api/weather/predict-grid` | Sin cambios de forma; un fallo de clima o predicción responde error (antes: 0.0). `source` = `"OPEN_METEO_ML_V2"`. |
| `GET /api/weather/best-window` | Sin cambios. |
| `POST /api/viajes/{id}/posicion` | Sin cambios de forma; usa `/v2/monitor/trip`. |

Clasificación: **aditivo** para consumidores (rutas y campos existentes se conservan), con un cambio semántico documentado (`probabilidadRl` nulo).
