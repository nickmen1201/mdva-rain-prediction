# Contract: features v1.0.0

Fuente de verdad en código: `mdva/features.py` (`FEATURE_CONTRACT_VERSION`, `RAW_INPUTS`, `FEATURES`). Documentación para revisores: `docs/features.md` (una prueba verifica que coincide con el código).

## Entradas crudas

| Campo | Tipo | Unidad | Rango válido | Origen (entrenamiento y producción) |
|---|---|---|---|---|
| `time_utc` | instante con zona horaria | — | cualquiera | hora objetivo de la predicción |
| `temperature_2m` | float | °C | −5 … 45 | Open-Meteo forecast |
| `relative_humidity_2m` | float | % | 0 … 100 | Open-Meteo forecast |
| `dew_point_2m` | float | °C | −20 … 35 | Open-Meteo forecast |
| `cloud_cover` | float | % | 0 … 100 | Open-Meteo forecast |
| `wind_speed_10m` | float | m/s | 0 … 60 | Open-Meteo forecast (`wind_speed_unit=ms`) |
| `wind_direction_10m` | float | ° | 0 … 360 | Open-Meteo forecast |
| `pressure_msl` | float | hPa | 950 … 1050 | Open-Meteo forecast |
| `precipitation` | float | mm/h | 0 … 200 | Open-Meteo forecast (precipitación pronosticada) |
| `cape` | float | J/kg | 0 … 10000 | Open-Meteo forecast |

Rangos idénticos a los del contrato de datos `rain_hourly` (spec 003). Los nulos, campos faltantes e instantes sin zona horaria se rechazan.

## Features (orden fijo)

| # | Feature | Transformación |
|---|---|---|
| 1 | `temperature_2m` | identidad |
| 2 | `relative_humidity_2m` | identidad |
| 3 | `dew_point_depression` | `temperature_2m − dew_point_2m` |
| 4 | `cloud_cover` | identidad |
| 5 | `wind_u` | `−speed · sin(dir)` (componente zonal, m/s) |
| 6 | `wind_v` | `−speed · cos(dir)` (componente meridional, m/s) |
| 7 | `pressure_msl` | identidad |
| 8 | `precipitation_log1p` | `log(1 + precipitation)` |
| 9 | `cape_log1p` | `log(1 + cape)` |
| 10 | `hour_sin` | `sin(2π · hora_local / 24)` |
| 11 | `hour_cos` | `cos(2π · hora_local / 24)` |
| 12 | `month_sin` | `sin(2π · (mes_local − 1) / 12)` |
| 13 | `month_cos` | `cos(2π · (mes_local − 1) / 12)` |

`hora_local` y `mes_local` se derivan de `time_utc` en `America/Bogota` (UTC−5, sin horario de verano).

Clasificación frente al modelo anterior: **rompiente** (entradas `hora`/`mes` enteras y `precip_lag_1h_mm` se reemplazan por `time_utc` y nuevas variables). Los consumidores se adaptan en las specs 006 y 007.
