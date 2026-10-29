# Quickstart: validar el dataset reproducible

## 1. Construir desde cero

```bash
rm -rf data/raw/openmeteo data/interim/*.parquet data/processed/*.parquet   # conserva los CSV de SIATA
make data            # = uv run python -m mdva.dataset
```

Esperado: 8 descargas, `data/processed/rain_hourly.parquet` con 13 × 35 064 filas (menos las descartadas por nulos, ≤ 1 %), `reports/data_quality.json` con todas las reglas en OK.

## 2. Idempotencia y determinismo

```bash
make data
```

Esperado: 0 descargas y la misma `content_fingerprint` en `reports/data_quality.json`.

## 3. Quality gates (pruebas negativas)

```bash
make test   # tests/test_data_contract.py: rango, unidad, duplicado, hora faltante, columna faltante
```

Esperado: las 5 alteraciones fallan con `DataContractError` y un mensaje que nombra la regla.

## 4. Validación externa de la etiqueta

```bash
make validate-labels   # = uv run python -m mdva.label_validation
```

Esperado: `reports/metrics/label_validation.json` con el umbral calibrado en la primera mitad, métricas de la segunda mitad para las 13 estaciones (≥ 250 horas cada una), ventanas de 1/3/6 h, análisis de desfases y ciclo diurno.

## Verificación registrada (2026-10-28)

- Construcción desde cero: 8 descargas (~40 MB). La primera ejecución recibió HTTP 429 (límite por minuto) en la tercera petición pesada y se detuvo sin dejar archivos a medias; tras ajustar la política de reintentos, la segunda ejecución reutilizó los 3 años ya descargados y completó el resto en 28 s.
- Dataset: **455 832 filas** = 13 estaciones × 35 064 horas, 0 filas descartadas, cobertura 100 % por estación en las tres etapas, tasa de lluvia 19.0 % (umbral 0.5 mm/h).
- Idempotencia: la ejecución siguiente hizo **0 descargas** en 4 s; huella de contenido `57133164…5fc482` y SHA-256 del Parquet idénticos entre ejecuciones.
- Las 13 estaciones caen en 5 celdas ERA5 (`processed_summary.stations_by_era5_cell` en `reports/data_quality.json`).
