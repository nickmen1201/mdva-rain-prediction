---

description: "Task list for 006-ml-api-v2"
---

# Tasks: ML API v2 (contract-first) con el nuevo modelo

**Tests**: pedidos por la spec (contrato, RF-17, v1 intacto).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 `mdva` con dependencias base + extra `pipeline` en `pyproject.toml`/`uv.lock` (raíz), `uv sync --all-extras` en `Makefile` y `.github/workflows/ci-python.yml`; `services/ml_api/pyproject.toml` con `mdva` (ruta) y dev `openapi-spec-validator`, `pyyaml`; `services/ml_api/uv.lock`

## Phase 2: User Story 2 - El contrato manda (Priority: P1)

- [X] T002 [US2] Test de validez del contrato y de coincidencia con el servicio en `services/ml_api/tests/test_contract.py` (falla hasta T004)

## Phase 3: User Story 3 - Monitoreo (Priority: P2)

- [X] T003 [US3] Reglas RF-17 como función pura en `services/ml_api/monitoring.py`, usadas por v1 en `services/ml_api/main.py`; tests de la tabla en `services/ml_api/tests/test_monitoring_rules.py`

## Phase 4: User Story 1 + 4 - Predicción v2 y arranque verificable (Priority: P1/P2) 🎯 MVP

- [X] T004 [US1] Router `/v2` en `services/ml_api/v2.py` (health, predict, batch, monitor/trip, Problem Details, lifespan) e inclusión en `services/ml_api/main.py`; tests en `services/ml_api/tests/test_v2.py`
- [X] T005 [US4] Imagen: `services/ml_api/Dockerfile` instala `mdva` y copia `models/rain_classifier/`; `.dockerignore`; README del servicio

## Phase 5: Polish

- [X] T006 Smoke test con verificaciones v2 en `tests/e2e/smoke_stack.py`; stack reconstruido; lote de 81 registros < 1 s; cerrar la spec

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006.
