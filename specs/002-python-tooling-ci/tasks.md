---

description: "Task list for 002-python-tooling-ci"
---

# Tasks: Tooling Python, calidad automatizada y CI

**Input**: Design documents from `/specs/002-python-tooling-ci/`

**Prerequisites**: plan.md, spec.md, research.md, contracts/, quickstart.md

**Tests**: pedidos explícitamente por la spec (US4: caracterización del servicio ML) y por FR-008/FR-009.

**Organization**: por historia de usuario; un commit por tarea, sin trailers de coautoría.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Crear `.python-version` (3.11) y `pyproject.toml` raíz del paquete `mdva` (dependencias de R2, grupo dev con ruff y pytest, `[tool.ruff]` y `[tool.pytest.ini_options]` de R4/R5); generar `uv.lock`

---

## Phase 2: Foundational

- [X] T002 Crear el `Makefile` raíz con los objetivos de `contracts/developer-commands.md`

**Checkpoint**: `make requirements` (o `uv sync`) instala el entorno raíz

---

## Phase 3: User Story 1 - Entorno Python reproducible (Priority: P1) 🎯 MVP

**Goal**: los 3 proyectos con versiones fijadas e imágenes que instalan desde el lock

**Independent Test**: `uv sync --frozen` por proyecto; `pip freeze` de las imágenes vs freezes guardados

- [ ] T003 [US1] `services/ml_api/pyproject.toml` + `uv.lock` con las versiones de R2; `services/ml_api/Dockerfile` instala con `uv sync --frozen --no-dev` (R3); eliminar `services/ml_api/requirements.txt`; ajustar `.dockerignore` raíz para excluir `.venv`
- [ ] T004 [US1] `services/routing_api/pyproject.toml` + `uv.lock` con las versiones de R2; `services/routing_api/Dockerfile` con uv (R3); `services/routing_api/.dockerignore` (excluye `.venv`, `__pycache__`, `tests`); eliminar `services/routing_api/requirements.txt`
- [ ] T005 [US1] Reconstruir las imágenes y comparar `pip freeze` con los freezes del 2026-10-28; registrar el resultado en `specs/002-python-tooling-ci/quickstart.md`

---

## Phase 4: User Story 4 - Comportamiento del servicio ML congelado en tests (Priority: P2)

**Goal**: tests de caracterización del servicio ML y de funciones puras del routing service

**Independent Test**: `make test`

- [ ] T006 [P] [US4] Tests de caracterización en `services/ml_api/tests/test_api.py` (health, raíz, `/predecir/{modelo}`, `/predecir/ambos`, 422 por hora/mes fuera de rango) y `services/ml_api/tests/test_monitoreo.py` (tabla completa de RF-17 con `monkeypatch` sobre `main.predecir`)
- [ ] T007 [P] [US4] Tests de funciones puras en `services/routing_api/tests/test_use_case_helpers.py` (`_haversine`, `_encode_polyline`, `_bearing_to_direction`)
- [ ] T008 [P] [US4] Test de rutas en `tests/test_config.py`

---

## Phase 5: User Story 2 - Cada push se verifica (Priority: P1)

**Goal**: lint/format en verde y workflows de CI por ecosistema

**Independent Test**: `make lint`; prueba negativa del quickstart; CI en verde

- [ ] T009 [US2] Aplicar `ruff check --fix` y `ruff format` a todo el código Python y corregir a mano los hallazgos restantes, sin cambiar comportamiento (verificado con `make test`)
- [ ] T010 [P] [US2] Eliminar la variable sin uso `heatmapCenter` en `apps/frontend/src/pages/EnRuta.jsx` (R9)
- [ ] T011 [US2] Separar `.github/workflows/ci-frontend.yml` (lint + build) de `ci-backend.yml`; crear `.github/workflows/ci-python.yml` con jobs `lint` y `test` (matriz de 3 proyectos)

---

## Phase 6: User Story 3 - Credenciales filtradas se detectan (Priority: P2)

**Goal**: gitleaks en CI y localmente

**Independent Test**: `make secrets` y prueba negativa del quickstart

- [ ] T012 [US3] Agregar `.gitleaksignore` (falso positivo de R6) y el job `secrets` en `.github/workflows/ci-python.yml`; ejecutar la prueba negativa local

---

## Phase 7: Polish & Cross-Cutting

- [ ] T013 Documentar en `README.md` (sección "Desarrollo") los objetivos del Makefile con sus equivalentes para Windows, y actualizar `CLAUDE.md` (versión real de scikit-learn por servicio, comandos uv)
- [ ] T014 Verificación final: `make clean`, stack reconstruido, smoke test idéntico a la línea base, CI en verde en GitHub; cerrar la spec

---

## Dependencies & Execution Order

- T001 → T002 → (T003, T004) → T005 → (T006, T007, T008 en paralelo) → T009 → (T010, T011) → T012 → T013 → T014.
- T009 va después de los tests para que el formateo masivo quede verificado por ellos.

## Implementation Strategy

1. US1 primero: sin entornos reproducibles no hay CI confiable.
2. Los tests de caracterización (US4) se escriben contra el código actual **antes** del formateo masivo (T009).
3. La CI (US2, US3) se activa al final, cuando todo pasa en local.
