# Data Model: Dataset reproducible de lluvia

## Station (`data/external/siata_stations.csv`)

| Campo | Tipo | Regla |
|---|---|---|
| `station_id` | int | único; código SIATA |
| `name` | str | no nulo |
| `municipality` | str | no nulo |
| `latitude` | float | 6.0 … 6.6 |
| `longitude` | float | −75.8 … −75.2 |

## RawDownload (`data/raw/MANIFEST.json`)

| Campo | Tipo | Regla |
|---|---|---|
| `path` | str | relativo a la raíz del repo; único |
| `source` | str | `openmeteo-forecast` · `openmeteo-era5` · `siata` |
| `url` | str | URL exacta (sin credenciales) o `null` si se colocó a mano |
| `sha256` | str | 64 caracteres hex |
| `downloaded_at_utc` | str | ISO 8601 con `Z` |

## ForecastHour (`data/interim/openmeteo_forecast.parquet`)

Clave única: (`station_id`, `time_utc`).

| Columna | Tipo | Unidad | Rango |
|---|---|---|---|
| `station_id` | int64 | — | catálogo |
| `time_utc` | datetime64[us, UTC] | — | 2022-01-01T00 … 2025-12-31T23 |
| `temperature_2m` | float64 | °C | −5 … 45 |
| `relative_humidity_2m` | float64 | % | 0 … 100 |
| `dew_point_2m` | float64 | °C | −20 … 35 |
| `cloud_cover` | float64 | % | 0 … 100 |
| `wind_speed_10m` | float64 | m/s | 0 … 60 |
| `wind_direction_10m` | float64 | ° | 0 … 360 |
| `pressure_msl` | float64 | hPa | 950 … 1050 |
| `precipitation` | float64 | mm/h | 0 … 200 |
| `cape` | float64 | J/kg | 0 … 10000 |

## ReferenceHour (`data/interim/openmeteo_era5.parquet`)

Clave única: (`station_id`, `time_utc`). Columnas: `station_id`, `time_utc`, `precipitation_ref` (mm/h, 0 … 200), `era5_cell` (str, "lat,lon" de la celda devuelta; dtype `str` de pandas 3).

## RainHour (`data/processed/rain_hourly.parquet`) — contrato `rain_hourly` v1.0.0

ForecastHour + `latitude`, `longitude` (de Station) + `precipitation_ref` + `era5_cell` + `rain` (bool; `precipitation_ref ≥ LABEL_THRESHOLD_MM`) .

Reglas: sin duplicados de clave; cobertura ≥ 99 % por estación; nulos ≤ 1 % por columna y estación; filas con nulos en features o referencia se descartan antes de etiquetar (se cuentan en el reporte).

## SiataHour (derivado en memoria por `mdva.label_validation`)

| Campo | Tipo | Regla |
|---|---|---|
| `station_id` | int | catálogo |
| `time_utc` | datetime UTC | hora local + 5 h |
| `precip_obs_mm` | float | suma de minutos con calidad 1 y valor ≥ 0 |
| `valid_minutes` | int | ≥ 50 para usarse |
| `rain_obs` | bool | `precip_obs_mm ≥ 0.1` |

## Reportes

- `reports/data_quality.json`: por etapa → reglas evaluadas (nombre, OK/FALLA, detalle), conteos, nulos y cobertura por estación, huellas de contenido.
- `reports/metrics/label_validation.json`: umbral calibrado y frecuencias de la mitad de calibración; métricas de la mitad de validación (por estación y totales; ventanas 1/3/6 h; etiqueta y pronóstico crudo); análisis de desfases −8…+8 h; ciclo diurno de cada fuente; estaciones por celda ERA5.
