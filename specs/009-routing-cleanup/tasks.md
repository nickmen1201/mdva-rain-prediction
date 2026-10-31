---

description: "Task list for 009-routing-cleanup"
---

# Tasks: Routing service — limpieza

**Tests**: pedidos por la spec (SC-002); todos sin red ni grafo OSM real.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 [P] Grafo sintético reutilizable en `services/routing_api/tests/conftest.py` (autopista larga y rápida vs calle residencial corta, nombres de vía)
- [X] T002 [P] `infrastructure/nearest.py` (`NearestNodeIndex`) con `tests/test_nearest.py`

## Phase 2: User Story 1 + 2 + 3 - Señal de lluvia única, sin datos inventados, caché por clave (Priority: P1/P2) 🎯 MVP

- [X] T003 [US1] [US2] [US3] `infrastructure/rain_signal.py` (`RainSignalClient`, `TTLCache`, `RainSignal`) con `tests/test_rain_signal.py` (unidades verificadas, hora UTC en curso, 0.75 → ROJO, Open-Meteo caído, ML 422/caído, caché por clave con reloj inyectable, no cachear fallos)
- [X] T004 [US1] Eliminar `domain/rain_model.py`, `train_rain_model.py`, `cache/rain_model.joblib`, `infrastructure/weather_service.py`; `presentation/dependencies.py` con `RainSignalClient`; variables `RAIN_MODEL_PATH` fuera del Dockerfile y compose

## Phase 3: User Story 4 - Tiempos reales y pasos (Priority: P2)

- [X] T005 [US4] `osmnx_map_repository.py`: velocidades y `travel_time` al cargar (y re-guardar la caché), logging
- [X] T006 [US4] `networkx_routing_service.py`: costos `fastest`/`shortest`/`dryest`, bicicleta ≤ 15 km/h, factor RF-10, nodo más cercano propio; `application/navigation.py` (pasos por vía); `dtos.py`/`use_cases.py` con los campos del contrato; `tests/test_routing_weights.py` y `tests/test_navigation.py`; actualizar `test_spring_duration.py`

## Phase 4: User Story 5 - Configuración y ML API sin v1 (Priority: P3)

- [X] T007 [US5] `main.py`: CORS por `CORS_ALLOWED_ORIGINS`, logging; `tests/test_app.py` (CORS, `/health`); quitar `scikit-learn`/`joblib`/`pandas` de `pyproject.toml` y regenerar `uv.lock`
- [X] T008 [US5] ML API: retirar `/predecir/*`, `/monitorear/trayecto`, `load_models` y `models/*.pkl`; ajustar `services/ml_api/tests`, README del servicio y el smoke test; charter 2.0.0 (RF-17, RF-22, RF-23)

## Phase 5: Polish

- [X] T009 Stack reconstruido (grafo en caché recalculado con tiempos), smoke test, duración de la ruta de ~5 km, `git ls-files` sin artefactos; README del routing service; cerrar la spec

## Dependencies & Execution Order

(T001, T002) → T003 → T004 → T005 → T006 → T007 → T008 → T009.
