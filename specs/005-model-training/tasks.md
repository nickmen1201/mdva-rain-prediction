---

description: "Task list for 005-model-training"
---

# Tasks: Entrenamiento con validación temporal, baselines y calibración

**Input**: Design documents from `/specs/005-model-training/`

**Tests**: pedidos por la spec (SC-001, SC-004) y por FR-009.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Agregar `matplotlib` a `pyproject.toml` (versión fijada) y `uv.lock`; objetivo `train` en el `Makefile`

## Phase 2: Foundational

- [X] T002 [P] Splits temporales en `mdva/modeling/splits.py` con tests en `tests/test_splits.py` (fronteras, separación de 24 h, exclusión de junio–julio de 2022, sin solapamientos)
- [X] T003 [P] Baselines en `mdva/modeling/baselines.py` (climatología, pronóstico crudo, persistencia) con tests en `tests/test_baselines.py`
- [X] T004 [P] Métricas en `mdva/modeling/evaluate.py` (ROC-AUC, PR-AUC, Brier, log loss, BSS, ECE, confiabilidad, bootstrap por días con diferencias pareadas, niveles de alerta) con tests en `tests/test_evaluate.py`

## Phase 3: User Story 1 - Modelo reproducible con un comando (Priority: P1) 🎯 MVP

- [X] T005 [US1] Reescribir `mdva/modeling/train.py` (selección por log loss, calibración con elección de método por sub-split, metadatos, registro de corrida) y `mdva/modeling/predict.py` (carga con verificación de versiones, `predict_proba`, `alert_level`) con tests en `tests/test_predict.py`

## Phase 4: User Story 2 + 3 - Evaluación honesta y probabilidades calibradas (Priority: P1/P2)

- [X] T006 [US2] Evaluación en prueba frente a baselines con IC, confiabilidad y niveles de alerta en `mdva/modeling/train.py`; figuras en `mdva/plots.py`

## Phase 5: User Story 4 - Validación externa (Priority: P2)

- [X] T007 [US4] Validación externa contra SIATA en `mdva/modeling/evaluate.py` y su inclusión en el reporte

## Phase 6: User Story 5 - Model card (Priority: P3)

- [X] T008 [US5] `mdva/modeling/model_card.py` y test de sincronía en `tests/test_model_card.py`

## Phase 7: Ejecución y cierre

- [X] T009 Ejecutar `make train` dos veces (determinismo), versionar `models/rain_classifier/1.0.0/`, `reports/metrics/rain_classifier/1.0.0/metrics.json`, figuras y registro de corrida; registrar resultados en `specs/005-model-training/quickstart.md`
- [X] T010 Verificar SC-001…SC-005 y cerrar la spec

## Dependencies & Execution Order

T001 → (T002, T003, T004) → T005 → T006 → T007 → T008 → T009 → T010.
