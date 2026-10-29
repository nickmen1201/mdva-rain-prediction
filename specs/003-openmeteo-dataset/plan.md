# Implementation Plan: Dataset reproducible de lluvia (Open-Meteo) con validación externa SIATA

**Branch**: `003-openmeteo-dataset` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-openmeteo-dataset/spec.md`

## Summary

`python -m mdva.dataset` descarga (con caché, manifiesto SHA-256 y escritura atómica) pronósticos archivados y precipitación ERA5 para las 13 estaciones SIATA, 2022–2025, en 8 peticiones; valida cada etapa contra un contrato declarativo y produce `data/processed/rain_hourly.parquet` con una etiqueta horaria cuyo umbral se calibra por igualación de frecuencias con la primera mitad del mes de pluviómetros SIATA. `python -m mdva.label_validation` reporta, con la segunda mitad, la fidelidad de la etiqueta y del pronóstico crudo frente a los pluviómetros.

## Technical Context

**Language/Version**: Python 3.11 (paquete `mdva`)

**Primary Dependencies**: pandas 3.1, numpy, requests (ya presentes). Nueva: `pyarrow` (Parquet; justificada en research R3).

**Storage**: archivos en `data/` (raw JSON/CSV, interim y processed en Parquet), ignorados por git

**Testing**: pytest (contrato, idempotencia de la descarga con un servidor simulado, calibración y métricas con datos sintéticos)

**Target Platform**: local / CI (los tests no usan red)

**Project Type**: pipeline de datos dentro del paquete CCDS v2

**Performance Goals**: dataset completo en < 30 min (medido: ~3 min de descarga)

**Constraints**: sin API keys; UTC en todo; raw inmutable; determinista

**Scale/Scope**: 13 estaciones × 35 064 h ≈ 456 k filas, 16 columnas

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| I. Intención cuesta abajo | Clarificaciones y hallazgos (umbral, zona horaria) en la spec antes del código. | ✅ |
| II. Reproducible | `make data` desde cero, manifiesto con hashes, huella de contenido. | ✅ |
| III. Secretos | La fuente no requiere credenciales. | ✅ |
| IV. Contract-first | [contracts/rain_hourly.v1.json](contracts/rain_hourly.v1.json) y [data-model.md](data-model.md) antes del código; el validador se prueba contra el contrato. | ✅ |
| V. Contratos y pipeline | raw → interim → processed, raw inmutable, quality gates dentro del pipeline, reporte. | ✅ |
| VI. Evaluación honesta | Umbral calibrado y validado en mitades disjuntas; limitación de resolución reportada. Misma fuente de features que en producción. | ✅ |
| VII. Sin datos fabricados | No se imputan nulos: las filas incompletas se descartan y se cuentan. | ✅ |
| Timestamps UTC | `timezone=GMT` en la fuente y `datetime64[ns, UTC]` en todas las etapas; SIATA convertido explícitamente. | ✅ |
| Dependencias justificadas | `pyarrow` (R3); argparse/logging de la stdlib en lugar de typer/loguru (R8). | ✅ |

**Post-design re-check**: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/003-openmeteo-dataset/
├── plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/rain_hourly.v1.json
└── checklists/requirements.md
```

### Source Code (repository root)

```text
mdva/
├── config.py            # + LOCATIONS/PERIOD/LABEL_THRESHOLD_MM y rutas de reportes
├── data_contract.py     # contrato declarativo + validate() + DataContractError
├── openmeteo.py         # cliente: URLs, unidades, reintentos, escritura atómica, manifiesto
├── dataset.py           # CLI: raw → interim → processed + reporte de calidad
└── label_validation.py  # CLI: calibración del umbral y validación externa SIATA
tests/
├── test_data_contract.py
├── test_openmeteo.py
├── test_dataset.py
└── test_label_validation.py
Makefile                 # + data, validate-labels
data/external/siata_stations.csv   (generado, ignorado por git)
reports/data_quality.json, reports/metrics/label_validation.json   (generados, versionados)
```

**Structure Decision**: módulos del paquete CCDS v2 (`dataset.py` como en la plantilla), con el cliente HTTP y el contrato separados para poder probarlos sin red.

## Complexity Tracking

Sin violaciones.
