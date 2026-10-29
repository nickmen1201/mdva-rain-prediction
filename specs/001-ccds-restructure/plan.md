# Implementation Plan: Reestructuración Cookiecutter Data Science v2

**Branch**: `001-ccds-restructure` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-ccds-restructure/spec.md`

## Summary

Mover el repositorio a la convención CCDS v2 (paquete `mdva/`, `data/`, `models/`, `notebooks/`, `references/`, `reports/`, `docs/`) y separar el producto en `services/` (APIs Python) y `apps/` (Backend y Frontend), eliminando archivos sin uso. Todo se hace con `git mv` para conservar el historial, ajustando solo la configuración que apunta a las rutas (Compose, Dockerfiles, CI, docs) y dos rutas en código Python (carpeta de modelos del servicio ML y rutas del script de entrenamiento). Un smoke test de punta a punta, ejecutado antes y después, prueba que el comportamiento no cambió.

## Technical Context

**Language/Version**: Python 3.11 (servicios y paquete `mdva`), Java 21 (Backend), Node 20 (Frontend)

**Primary Dependencies**: sin dependencias nuevas. El smoke test usa solo la librería estándar de Python.

**Storage**: PostgreSQL 16 (volumen existente, debe reutilizarse); archivos del grafo OSM en el volumen `routing_graph_cache`

**Testing**: Gradle `test` (Backend), `npm run build` (Frontend), `tests/e2e/smoke_stack.py` (stack completo)

**Target Platform**: Docker Compose en Windows 11 (dev); Linux en contenedores

**Project Type**: monorepo de ciencia de datos con servicios web (CCDS v2 + `services/` + `apps/`)

**Performance Goals**: N/A (sin cambios de comportamiento)

**Constraints**: 0 cambios observables en endpoints y puertos; volúmenes reutilizados; historial de git preservado; renombres solo de mayúsculas seguros en NTFS

**Scale/Scope**: ~260 archivos versionados; ~25 movimientos de carpeta o archivo y ~10 eliminaciones

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cómo se cumple | Estado |
|---|---|---|
| I. La intención fluye cuesta abajo | La spec define el mapa de reubicación; no se agrega comportamiento. Los requisitos del charter §4 se verifican con el smoke test. | ✅ |
| II. Reproducible desde checkout limpio | Se elimina la ruta absoluta del script de entrenamiento (`C:/Users/Luis Seoanes/...`); el nombre de proyecto de Compose se fija para no depender de la carpeta. | ✅ |
| III. Secretos fuera del repo | Sin cambios; `apps/frontend/.env` sigue ignorado tras el movimiento (se verifica). | ✅ |
| IV. Contract-first | El "contrato" de esta spec es estructural: [contracts/repo-layout.md](contracts/repo-layout.md) y [contracts/stack-services.md](contracts/stack-services.md), escritos antes de mover. No hay cambios de API. | ✅ |
| V. Contratos de datos y pipeline | `data/raw` se crea vacío e ignorado; el CSV crudo de SIATA queda en `raw` (inmutable) y el derivado en `interim`. | ✅ |
| VI. Evaluación honesta de ML | No aplica (no se entrena ni se evalúa). Los modelos se mueven sin tocarlos. | N/A |
| VII. Sin datos fabricados | No aplica. | N/A |
| Restricciones: estructura CCDS v2 | Es el objetivo de la spec. | ✅ |
| Restricciones: versiones fijadas en un solo lugar | Se difiere a la spec 002 (`pyproject.toml` + `uv.lock`); el servicio ML conserva su `requirements.txt` fijado. | ✅ (diferido, justificado) |
| Flujo: commit por fase y por tarea, sin coautoría | Se aplica. | ✅ |

**Post-design re-check**: sin violaciones. La única desviación de la plantilla CCDS v2 (servicios y apps en subcarpetas) está justificada en el charter §2.

## Project Structure

### Documentation (this feature)

```text
specs/001-ccds-restructure/
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   ├── repo-layout.md
│   └── stack-services.md
├── checklists/requirements.md
└── tasks.md
```

No hay `data-model.md`: la spec no introduce entidades de datos. Las entidades de la spec (mapa de reubicación, servicio del stack) están formalizadas en los contratos.

### Source Code (repository root)

```text
.
├── .specify/  specs/                      # SDD (sin cambios)
├── .github/workflows/{ci-backend.yml, release.yml}
├── docker-compose.dev.yml  docker-compose.prod.yml
├── .dockerignore                          # lista de permitidos para el build del servicio ML
├── data/{raw/siata, interim/siata, processed, external}/   # ignorado (salvo .gitkeep)
├── docs/{informe-tecnico.md, manual-*.md, backend-tests.md, sprints/}
├── models/{random_forest.pkl, regresion_logistica.pkl}
├── notebooks/1.0-nm-analisis-espacial-siata-vs-openmeteo.ipynb
├── references/{informe-proyecto-mva.pdf, wiki-general.pdf}
├── reports/figures/
├── mdva/{__init__.py, config.py, modeling/{__init__.py, train.py}}
├── services/
│   ├── ml_api/{main.py, Dockerfile, requirements.txt, railway.toml, README.md}
│   └── routing_api/{domain, application, infrastructure, presentation, cache, main.py, ...}
├── apps/
│   ├── backend/   (antes Backend/, contenido intacto + .dockerignore)
│   └── frontend/  (antes Frontend/, contenido intacto)
├── db/{init-docker.sql, seeds/*.csv, scripts/webscraper_municipios.py}
└── tests/e2e/smoke_stack.py
```

**Structure Decision**: CCDS v2 en la raíz, con el paquete `mdva/`; las piezas de producto se aíslan en `services/` (Python) y `apps/` (Java y JS) para que el trabajo de ciencia de datos sea lo primero que ve el revisor (charter §2).

## Complexity Tracking

Sin violaciones de la constitución que justificar.
