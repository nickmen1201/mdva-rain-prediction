---

description: "Task list for 003-openmeteo-dataset"
---

# Tasks: Dataset reproducible de lluvia (Open-Meteo) con validación externa SIATA

**Input**: Design documents from `/specs/003-openmeteo-dataset/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: pedidos por la spec (SC-004: 5 alteraciones que deben detener el pipeline) y necesarios para validar sin red.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Agregar `pyarrow` a `pyproject.toml` (versión fijada), actualizar `uv.lock`; agregar a `mdva/config.py` las constantes del dataset (periodo, variables, `LABEL_THRESHOLD_MM`, rutas `REPORTS_DIR/metrics`) y los objetivos `data` y `validate-labels` al `Makefile`

---

## Phase 2: Foundational

- [ ] T002 [P] Contrato declarativo y validador en `mdva/data_contract.py` (columnas, tipos, unidades, rangos, nulos, clave única, cobertura; reporte por regla; `DataContractError`) con tests de las 5 alteraciones en `tests/test_data_contract.py`
- [ ] T003 [P] Cliente Open-Meteo en `mdva/openmeteo.py` (construcción de URLs con unidades explícitas y UTC, verificación de `hourly_units`, reintentos exponenciales ante 429/5xx, escritura atómica, manifiesto SHA-256) con tests sin red en `tests/test_openmeteo.py`

**Checkpoint**: contrato y descarga probados sin red

---

## Phase 3: User Story 1 - Reproducir el dataset con un comando (Priority: P1) 🎯 MVP

**Goal**: `make data` construye `data/processed/rain_hourly.parquet` desde cero y es idempotente

**Independent Test**: quickstart §1 y §2

- [ ] T004 [US1] Catálogo de estaciones y etapa raw en `mdva/dataset.py` (deriva `data/external/siata_stations.csv` del CSV crudo, registra los CSV de SIATA en el manifiesto, descarga 2 fuentes × 4 años)
- [ ] T005 [US1] Etapas interim y processed en `mdva/dataset.py` (formato largo, unión, descarte de filas incompletas, etiqueta con `LABEL_THRESHOLD_MM`, huella de contenido) con tests sobre respuestas sintéticas en `tests/test_dataset.py`
- [ ] T006 [US1] Ejecutar `make data` desde cero y dos veces seguidas; registrar tiempos, filas, descargas y huellas en `specs/003-openmeteo-dataset/quickstart.md`

---

## Phase 4: User Story 2 - Datos defectuosos detienen el pipeline (Priority: P1)

**Goal**: cada etapa valida contra el contrato y escribe `reports/data_quality.json`

**Independent Test**: `make test` (alteraciones) y revisión del reporte

- [ ] T007 [US2] Integrar `validate()` en las salidas de interim y processed de `mdva/dataset.py`, sin promover datos si falla, y escribir `reports/data_quality.json`; test de que una etapa con datos inválidos no escribe su salida en `tests/test_dataset.py`

---

## Phase 5: User Story 3 - Fidelidad de la etiqueta frente a pluviómetros (Priority: P2)

**Goal**: umbral calibrado sin fuga y reporte de validación externa

**Independent Test**: quickstart §4

- [ ] T008 [US3] `mdva/label_validation.py`: horas SIATA (UTC−5 → UTC, ≥ 50 minutos, calidad 1), división en mitades, calibración por igualación de frecuencias, métricas (precisión, sensibilidad, F1, kappa) por estación y totales para la etiqueta y el pronóstico crudo en ventanas 1/3/6 h, desfases −8…+8 h, ciclo diurno y estaciones por celda; tests con datos sintéticos en `tests/test_label_validation.py`
- [ ] T009 [US3] Ejecutar `make validate-labels`, fijar el umbral resultante en `mdva/config.py`, reconstruir el dataset con ese umbral y versionar `reports/metrics/label_validation.json` y `reports/data_quality.json`

---

## Phase 6: Polish

- [ ] T010 Documentar en `README.md` (sección Datos) la fuente, la etiqueta, el umbral y la limitación de resolución, con los números del reporte; verificar SC-001…SC-005 y cerrar la spec

---

## Dependencies & Execution Order

T001 → (T002, T003) → T004 → T005 → T006 → T007 → T008 → T009 → T010. T009 reconstruye el dataset porque el umbral final sale de la calibración.

## Implementation Strategy

MVP = US1 (dataset reproducible). US2 endurece el pipeline; US3 aporta la evidencia sobre la etiqueta que usará la spec 005.
