# Implementation Plan: Tooling Python, calidad automatizada y CI

**Branch**: `002-python-tooling-ci` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-python-tooling-ci/spec.md`

## Summary

Cada proyecto Python (`mdva` en la raíz, `services/ml_api`, `services/routing_api`) declara sus dependencias en `pyproject.toml` con las versiones que corren hoy y las bloquea con `uv.lock`; las imágenes instalan desde el lock. Ruff (lint + formato) y pytest se ejecutan con un Makefile estilo CCDS v2 y en un nuevo workflow `ci-python.yml`, junto con gitleaks sobre el historial completo. Se agregan tests de caracterización del servicio ML (incluida la tabla de reglas de monitoreo) y tests de funciones puras del routing service, para poder refactorizar después sin perder comportamiento.

## Technical Context

**Language/Version**: Python 3.11 (fijado con `.python-version`); Node 20 (Frontend en CI)

**Primary Dependencies** (nuevas, justificadas — constitución):
- `uv` 0.12.5: entornos y lockfiles reproducibles; la stdlib no resuelve dependencias.
- `ruff`: lint y formato en una sola herramienta; la stdlib no tiene linter.
- `pytest`: runner de tests con fixtures y `monkeypatch`; `unittest` sería más verboso para la tabla de reglas.
- `httpx`: requerido por `fastapi.testclient`.
- gitleaks v8.30.1 (imagen Docker): escaneo de secretos exigido por la constitución III.

**Storage**: N/A

**Testing**: pytest (3 proyectos), ESLint (Frontend), Gradle (Backend, sin cambios), smoke test e2e

**Target Platform**: GitHub Actions (ubuntu-latest); Windows 11 local

**Project Type**: monorepo CCDS v2 con servicios

**Performance Goals**: CI de Python en menos de 5 minutos

**Constraints**: 0 cambios de versiones respecto a los contenedores actuales; tests sin red; sin desactivar reglas de lint existentes

**Scale/Scope**: ~25 archivos Python; 3 lockfiles; 3 workflows

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| I. Intención cuesta abajo | Sin cambios de comportamiento; las clarificaciones quedan en la spec. | ✅ |
| II. Reproducible | Lockfiles por proyecto, Python fijado, `--frozen` en Docker y CI. | ✅ |
| III. Secretos | gitleaks en CI sobre todo el historial; un falso positivo documentado. | ✅ |
| IV. Contract-first | [contracts/developer-commands.md](contracts/developer-commands.md) define comandos y checks antes de implementarlos. Sin cambios de API. | ✅ |
| V–VII | No aplican (sin datos ni entrenamiento). | N/A |
| Automatizar lo verificable | Ruff, pytest, ESLint y gitleaks en CI; rojo bloquea el merge. | ✅ |
| Dependencias nuevas justificadas | Ver Technical Context. | ✅ |
| Versiones en un solo lugar por ecosistema | Un `pyproject.toml` + `uv.lock` por proyecto Python; se eliminan los `requirements.txt`. | ✅ |

**Post-design re-check**: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/002-python-tooling-ci/
├── plan.md  research.md  quickstart.md  tasks.md
├── contracts/developer-commands.md
└── checklists/requirements.md
```

No hay `data-model.md`: la spec no introduce entidades de datos.

### Source Code (repository root)

```text
.
├── pyproject.toml  uv.lock  .python-version     # proyecto mdva + config de ruff y pytest
├── Makefile                                    # objetivos CCDS v2
├── .gitleaksignore
├── .github/workflows/{ci-python.yml, ci-backend.yml, ci-frontend.yml, release.yml}
├── tests/test_config.py
├── services/ml_api/{pyproject.toml, uv.lock, Dockerfile, tests/}
├── services/routing_api/{pyproject.toml, uv.lock, Dockerfile, .dockerignore, tests/}
└── apps/frontend/src/pages/EnRuta.jsx          # quitar variable sin uso
```

**Structure Decision**: un proyecto Python por carpeta desplegable (R1); la configuración de ruff y pytest vive una sola vez en la raíz.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Tres lockfiles en lugar de uno | Los servicios usan versiones incompatibles de FastAPI y scikit-learn | Un lock común cambiaría versiones en producción (FR-002) |
