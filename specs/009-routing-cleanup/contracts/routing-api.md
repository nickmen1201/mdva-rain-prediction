# Contract: routing service tras la limpieza

## Dependencias consumidas

| Servicio | Llamada |
|---|---|
| Open-Meteo Forecast | `GET /v1/forecast?latitude&longitude&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,cloud_cover,wind_speed_10m,wind_direction_10m,pressure_msl,precipitation,cape&forecast_days=1&timezone=GMT&wind_speed_unit=ms&temperature_unit=celsius&precipitation_unit=mm` (unidades verificadas) |
| ML API v2 | `POST /v2/predict` `{time_utc, <9 variables>}` → `{probability, alert_level, model_version}` (contrato: `specs/006-ml-api-v2/contracts/openapi-v2.yaml`) |

## Campos de lluvia (todas las respuestas de ruta)

| Campo | Antes | Después | Clasificación |
|---|---|---|---|
| `rain_probability` | 0–100, máximo entre regresor y RF v1 | 0–1 del modelo v2, o `null` si `clima_disponible=false` | rompiente (escala) — sin consumidores |
| `alerta_nivel` | umbral `>= 0.70` | RF-10: `> 0.70` ROJO, `≥ 0.40` AMARILLO; `null` sin clima | semántico |
| `clima_disponible` | — | `bool` | aditivo |
| `model_version` | — | versión del modelo v2 o `null` | aditivo |
| `rain_factor` | penalización del regresor (1–2+) | factor RF-10 aplicado al tiempo (1.00/1.20/1.35; 1.00 sin clima) | semántico |
| `rain_intensity_avg`, `elevation_avg`, `mdva_llueve`, `mdva_probabilidad_rf`, `mdva_probabilidad_rl`, `mdva_temperatura_c`, `mdva_humedad_pct`, `mdva_cobertura_nubosa_pct`, `mdva_velocidad_viento_ms` | presentes | eliminados | rompiente — sin consumidores (el Backend dejó de leerlos en la spec 008) |
| `total_rain_intensity_avg` (`/route/multi`) | promedio entre tramos | eliminado | rompiente — sin consumidores |

## Endpoints (rutas sin cambios, RF-15)

| Endpoint | Cambio |
|---|---|
| `POST /api/v1/route` | `options[]` con `travel_time_seconds` = Σ `travel_time` × factor. |
| `POST /api/v1/route/multi` | Un tramo por par de puntos; la señal de lluvia es la del origen del viaje (una consulta). |
| `POST /api/v1/route/spring` | `duracionSegundos` base (spec 008); pasos agrupados por vía con nombre. |
| `POST /api/v1/route/metrics` | `{rain_probability, alerta_nivel, clima_disponible, model_version, time_utc}`. |
| `GET /health` | Sin cambios. |

## CORS

`CORS_ALLOWED_ORIGINS` (coma-separado). Vacío → sin orígenes cruzados.

## ML API (retiro de v1)

`/predecir/{modelo}`, `/predecir/ambos`, `/monitorear/trayecto` → eliminados (404). `/`, `/health`, `/v2/*` sin cambios. **Rompiente**, sin consumidores tras esta spec.
