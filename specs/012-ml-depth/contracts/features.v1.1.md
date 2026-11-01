# Contract: features del modelo de lluvia v1.1.0

Implementación única: `mdva/features.py` (`FEATURE_CONTRACT_VERSION = "1.1.0"`). Documentación para lectores: `docs/features.md`. Diff respecto de [v1.0.0](../../004-feature-contract/contracts/features.v1.md):

## Entradas (todas obligatorias; ninguna se rellena)

| Grupo | Campos | Unidad y rango | Cambio |
|---|---|---|---|
| Instante | `time_utc` (ISO 8601 con zona) | — | sin cambio |
| Pronóstico de la hora | `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `cloud_cover`, `wind_speed_10m`, `wind_direction_10m`, `pressure_msl`, `precipitation`, `cape` | contrato `rain_hourly` | sin cambio |
| Ventana del mismo pronóstico | `precipitation_prev2`, `precipitation_prev1`, `precipitation_next1`, `precipitation_next2`, `cloud_cover_prev1`, `cloud_cover_next1`, `cape_prev1`, `cape_next1` | las de su variable | **nuevo** |
| Ubicación | `latitude` ∈ [6.0, 6.6], `longitude` ∈ [−75.8, −75.2] | ° | **nuevo** |

`prevN`/`nextN` = valor de la variable N horas antes/después de `time_utc` **en la misma corrida del pronóstico** (la serie horaria que devuelve Open-Meteo). En el dataset se arman con `forecast_window_inputs` (vecinos contiguos de la misma estación); una fila sin sus cuatro vecinos no se usa para entrenar ni se predice.

## Salida

24 features en este orden: las 13 de v1.0.0 (sin cambios), luego `precipitation_prev2_log1p`, `precipitation_prev1_log1p`, `precipitation_next1_log1p`, `precipitation_next2_log1p`, `cloud_cover_prev1`, `cloud_cover_next1`, `cape_prev1_log1p`, `cape_next1_log1p`, `precipitation_5h_log1p`, `latitude`, `longitude`.

## Compatibilidad

- **Rompiente** para el ML API (campos obligatorios nuevos → `openapi-v2.yaml` 2.1.0). Sus dos consumidores (Backend y routing service) se actualizan en la misma spec y ya envían los campos (los campos extra eran ignorados por la versión 2.0.0, así que el orden de despliegue no rompe nada).
- El modelo 1.0.0 usa `BASE_FEATURES` (las 13 primeras) y se conserva solo para la comparación pareada en `metrics.json`.
- Paridad: `tests/test_features.py` compara las features de entrenamiento (DataFrame) y de inferencia (registros JSON) con datos sintéticos y reales: diferencia máxima 0.
