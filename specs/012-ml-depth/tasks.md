---

description: "Task list for 012-ml-depth"
---

# Tasks: Profundidad de ML

**Tests**: pedidos por la spec (FR-001, FR-010) y por la constitución (paridad train/serve).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 [P] Holdout fresco 2026 en archivo aparte: `config.HOLDOUT_*`, `openmeteo.build_url(end_date)`, `dataset.run_holdout()` (mismos contratos con el periodo 2026), `make data-holdout`; tests en `tests/test_openmeteo.py`, `tests/test_dataset.py`
- [X] T002 [P] `mdva/modeling/cv.py` (folds *rolling origin*, máscara de desarrollo, `cross_validate` con OOF) con `tests/test_cv.py`
- [X] T003 [P] `mdva/modeling/search.py` (espacio declarado, 60 HGB + familias de referencia, regla de 1 EE) con `tests/test_search.py`
- [X] T004 [P] `mdva/modeling/analysis.py` (permutación con IC, PDP/ICE, segmentos, calibración *cross-fitted*, curvas de costo) y `mdva/modeling/calibration.py` (calibrador serializable) con `tests/test_analysis.py`

## Phase 2: User Story 1–5 - Estudio (Priority: P1) 🎯 MVP

- [X] T005 [US1] [US2] [US3] [US4] [US5] `mdva/modeling/study.py` (candidatas con CV temporal y espacial, búsqueda, ablación, curva de aprendizaje, interpretabilidad, errores, calibración, decisión, `decision_log`) + figuras en `mdva/plots.py`; `make study`; `reports/metrics/rain_classifier/study/study.json`

## Phase 3: User Story 3 + 6 - Contrato 1.1.0 y modelo final (Priority: P1)

- [X] T006 [US3] Contrato de features 1.1.0 en `mdva/features.py` (ventana del pronóstico + ubicación, `forecast_window_inputs`), `docs/features.md`, `contracts/features.v1.1.md`; tests de paridad en `tests/test_features.py`
- [X] T007 [US6] `mdva/modeling/train.py` 1.1.0 desde `study.json`: entrenamiento en desarrollo, mapa de calibración OOF, evaluación única en 2025 y 2026 contra baselines y 1.0.0, `decision_log`; `mdva/modeling/model_card.py` con las secciones nuevas; `tests/test_predict.py`, `tests/test_model_card.py`
- [X] T008 [US6] ML API con el contrato 2.1.0 (`contracts/openapi-v2.yaml`) y el modelo 1.1.0; Backend (`HourlyInputs`, `OpenMeteoForecastClient` con `past_days=1`) y routing service (`rain_signal.model_record`, `rain_grid`) envían ventana y ubicación; tests de los tres servicios

## Phase 4: User Story 7 - Notebook (Priority: P2)

- [X] T009 [US7] `notebooks/3.0-nm-evaluacion-y-calibracion.ipynb` generado y ejecutado desde `reports/` (`make notebook`), con salidas ligeras

## Phase 5: Polish

- [X] T010 Reproducibilidad (semillas fijas; determinismo de estudio → entrenamiento verificado de punta a punta en `tests/test_predict.py`), stack con el modelo 1.1.0 y smoke test; `quickstart.md` con verificación registrada; cerrar la spec

## Dependencies & Execution Order

(T001, T002, T003, T004) → T005 → T006 → T007 → T008 → T009 → T010.
