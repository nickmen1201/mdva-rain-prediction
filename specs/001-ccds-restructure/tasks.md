---

description: "Task list for 001-ccds-restructure"
---

# Tasks: Reestructuración Cookiecutter Data Science v2

**Input**: Design documents from `/specs/001-ccds-restructure/`

**Prerequisites**: plan.md, spec.md, research.md, contracts/, quickstart.md

**Tests**: la spec exige verificar que el comportamiento no cambia (US2, SC-003), así que se incluye el smoke test de punta a punta y se ejecuta antes de mover nada.

**Organization**: tareas agrupadas por historia de usuario. US2 (comportamiento idéntico) es P1 pero se valida al final porque depende de todos los movimientos; su prueba (T001–T002) se escribe primero.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias)
- **[Story]**: historia a la que pertenece (US1…US4)
- Un commit por tarea (Conventional Commits, sin trailers de coautoría)

---

## Phase 1: Setup

**Purpose**: prueba de regresión y línea base antes de tocar la estructura

- [X] T001 Crear el smoke test del stack en `tests/e2e/smoke_stack.py` (stdlib: health de ml/routing/backend, registro + login, `POST /predecir/ambos`, `POST /api/v1/route`, `POST /api/viajes/planificar`; salida JSON con el estado de cada verificación)
- [X] T002 Ejecutar la línea base con el stack actual y registrar el resultado y el conteo de usuarios en `specs/001-ccds-restructure/quickstart.md` (sección "Línea base registrada")

---

## Phase 2: Foundational

**Purpose**: garantías que deben existir antes de mover carpetas

- [X] T003 Fijar `name: monitoreo-de-variables-ambientales` en `docker-compose.dev.yml` y `docker-compose.prod.yml` (R1)
- [X] T004 Crear el esqueleto CCDS (`data/{raw,interim,processed,external}/.gitkeep`, `reports/figures/.gitkeep`), fusionar `Data-science/.gitignore` en `.gitignore` con reglas para `data/**`, y mover los CSV de SIATA a `data/raw/siata/` y `data/interim/siata/`

**Checkpoint**: volúmenes con nombre fijo y datos ignorados; se puede empezar a mover

---

## Phase 3: User Story 1 - El revisor entiende el proyecto por su estructura (Priority: P1) 🎯 MVP

**Goal**: el árbol del repo coincide con `contracts/repo-layout.md`

**Independent Test**: `ls` de la raíz y `git log --follow` sobre archivos movidos (quickstart §4)

- [X] T005 [US1] Mover `Backend/` → `apps/backend/`; actualizar `docker-compose.dev.yml`, `.github/workflows/ci.yml` → `.github/workflows/ci-backend.yml`, `.github/workflows/release.yml`; ajustar la ruta del `.env` en `apps/backend/src/main/resources/application-dev.yml` y `apps/backend/build.gradle.kts` (`../../.env`); reemplazar `apps/backend/dockerignore` por `apps/backend/.dockerignore` (R6)
- [X] T006 [US1] Mover `Frontend/` → `apps/frontend/`; actualizar `docker-compose.dev.yml`, `docker-compose.prod.yml`, el job de Frontend en `.github/workflows/ci-backend.yml` y la nota de `.env.example`
- [X] T007 [US1] Mover `Data-science/enrutamiento_ambiental/` → `services/routing_api/`; actualizar contextos en ambos compose
- [X] T008 [US1] Mover el servicio ML a `services/ml_api/` y los modelos a `models/`; `MDVA_MODELS_DIR` en `services/ml_api/main.py` (R4); Dockerfile con contexto raíz y `.dockerignore` de permitidos (R3); `services/ml_api/railway.toml` (R8); `services/ml_api/README.md` en reemplazo de los dos READMEs duplicados (D-05); contextos en ambos compose
- [X] T009 [US1] Crear `mdva/__init__.py`, `mdva/config.py` y `mdva/modeling/__init__.py`; mover `Data-science/train_models.py` → `mdva/modeling/train.py` resolviendo rutas con `mdva.config` y sin la ruta absoluta (R5); mover el notebook a `notebooks/1.0-nm-analisis-espacial-siata-vs-openmeteo.ipynb`
- [X] T010 [US1] Mover `DB/` → `db/` en dos pasos (R2): `db/init-docker.sql`, `db/seeds/*.csv`, `db/scripts/webscraper_municipios.py`; actualizar el montaje en ambos compose
- [X] T011 [P] [US1] Mover documentos a `docs/` y PDFs a `references/` según `contracts/repo-layout.md` (R9)

**Checkpoint**: estructura objetivo en su lugar

---

## Phase 4: User Story 3 - El repositorio no carga basura (Priority: P2)

**Goal**: sin archivos sin uso versionados

**Independent Test**: los archivos de la tabla "Eliminaciones" de `contracts/repo-layout.md` no aparecen en `git ls-files`

- [X] T012 [US3] Eliminar D-02 (`services/routing_api/scripts/train_rain_model.py`), D-04 (`services/routing_api/infrastructure/siata_live_service.py`), D-07 (`db/TIC1DB.sql`, `db/TIC1DB.backup`) y D-13 (`CONTEXT.md`); sacar del índice D-08 (`apps/backend/.idea/`, `apps/backend/.claude/`, `.vscode/settings.json`)

---

## Phase 5: User Story 4 - El despliegue de producción vuelve a construir (Priority: P3)

**Goal**: `docker-compose.prod.yml` construye el Backend

**Independent Test**: `docker compose -f docker-compose.prod.yml --env-file .env.example config -q` y build de la imagen del Backend

- [X] T013 [US4] Cambiar el Backend en `docker-compose.prod.yml` a `context: ./apps/backend` + `dockerfile: Dockerfile` (R7) y validar la configuración

---

## Phase 6: User Story 2 - El sistema funciona exactamente igual (Priority: P1)

**Goal**: mismo resultado del smoke test, de los tests y de los builds

**Independent Test**: quickstart §2 y §3

- [ ] T014 [US2] Reconstruir el stack, repetir el smoke test y el conteo de usuarios, correr `./gradlew test` en `apps/backend` y `npm run build` en `apps/frontend`; registrar los resultados en `specs/001-ccds-restructure/quickstart.md` (sección "Verificación registrada")

---

## Phase 7: Polish & Cross-Cutting

- [ ] T015 Actualizar rutas en `README.md` y `CLAUDE.md`; verificar SC-005 con el `git grep` del quickstart §4
- [ ] T016 Verificar SC-001…SC-006 y FR-012 (`.specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly`), marcar la spec como `Implemented` en `specs/001-ccds-restructure/spec.md`

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T004)** → **US1 (T005–T011)** → **US3 (T012)** → **US4 (T013)** → **US2 (T014)** → **Polish (T015–T016)**.
- Dentro de US1, T005–T010 tocan los compose y se hacen en secuencia; T011 es independiente ([P]).
- T012 depende de T007 y T010 (las rutas a eliminar ya están en su nueva ubicación).
- T014 depende de todas las tareas anteriores.

## Parallel Example: User Story 1

```text
T011 (documentos y PDFs) se puede hacer en paralelo con T005–T010.
```

## Implementation Strategy

1. Línea base (T001–T002) antes de cualquier movimiento.
2. US1 deja el MVP estructural; US3 y US4 son incrementos pequeños.
3. US2 es el gate final: si el smoke test difiere de la línea base, se corrige antes de cerrar la spec.
