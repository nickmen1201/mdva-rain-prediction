# Research: Tooling Python, calidad automatizada y CI

## R1. Gestor de entornos y lockfiles

- **Decision**: `uv` (0.12.5) con un proyecto por carpeta: raíz (`mdva`), `services/ml_api`, `services/routing_api`; cada uno con `pyproject.toml` + `uv.lock`, y Python fijado a 3.11 con `.python-version`.
- **Rationale**: uv genera lockfiles multiplataforma reproducibles, instala en segundos y ya está instalado en la máquina del autor. Proyectos separados porque las versiones de FastAPI (0.115.6 vs 0.162.0) y scikit-learn (1.8.0 vs 1.9.1) de los servicios son incompatibles entre sí (Clarifications).
- **Alternatives considered**: workspace de uv con un solo lock (obliga a una resolución común → cambia versiones); pip-tools (más lento, sin gestión de Python); Poetry (no gestiona la versión de Python, lock más lento).

## R2. Versiones a fijar

- **Decision**: dependencias directas fijadas con `==` a lo que reporta `pip freeze` en los contenedores el 2026-10-28; las transitivas las fija `uv.lock`.
  - `services/ml_api`: fastapi 0.115.6, uvicorn[standard] 0.32.1, scikit-learn 1.8.0, joblib 1.5.2, numpy 2.4.6, pydantic 2.10.3.
  - `services/routing_api`: fastapi[standard] 0.162.0, uvicorn 0.54.0, osmnx 2.1.1, networkx 3.6.1, pydantic 2.14.1, scikit-learn 1.9.1, pandas 3.1.0, joblib 1.6.0, requests 2.34.2, shapely 2.2.0.
  - raíz (`mdva`): numpy 2.4.6, pandas 3.1.0, scikit-learn 1.8.0 (la de los modelos de `models/`), joblib 1.5.2, requests 2.34.2.
- **Rationale**: FR-002 (comportamiento idéntico). El desajuste del routing service (modelo serializado con 1.8.0 y servido con 1.9.1) se preserva a propósito; ese modelo se elimina en la spec 009.
- **Verification**: comparar `pip freeze` de las imágenes nuevas con los freezes guardados.

## R3. Instalación en Docker

- **Decision**: copiar el binario de uv desde `ghcr.io/astral-sh/uv:0.12.5` y ejecutar `uv sync --frozen --no-dev --no-install-project`; el `PATH` apunta a `/app/.venv/bin`.
- **Rationale**: `--frozen` falla si el lock no corresponde al `pyproject.toml` (FR-003), así nunca se resuelve en el build.
- **Alternatives considered**: `uv export > requirements.txt` + pip (dos fuentes de verdad).

## R4. Lint y formato

- **Decision**: `ruff` (lint + format) configurado una vez en el `pyproject.toml` raíz: `line-length = 120`, `target-version = "py311"`, reglas `E`, `F`, `W`, `I`; se excluyen `notebooks/` y `.specify/`. Ruff toma la configuración del `pyproject.toml` más cercano que tenga `[tool.ruff]`; los de los servicios no la definen, así que aplica la raíz.
- **Rationale**: es la herramienta de la plantilla CCDS v2; una sola configuración para todo el repo.
- **Alternatives considered**: flake8 + black + isort (tres herramientas, más lento).

## R5. Tests

- **Decision**: `pytest` como dependencia de desarrollo de cada proyecto; `httpx` en el servicio ML para `fastapi.testclient`.
  - `tests/test_config.py` (raíz): rutas de `mdva.config`.
  - `services/ml_api/tests/`: tests de caracterización con los modelos reales de `models/` (versionados), sin red. Las reglas de monitoreo se prueban fijando la probabilidad actual con `monkeypatch` sobre `main.predecir`, para que no dependan del modelo.
  - `services/routing_api/tests/`: funciones puras del caso de uso (`_haversine`, `_encode_polyline`, `_bearing_to_direction`), sin grafo ni red.
- **Rationale**: FR-008, FR-009 y la regla de "tests antes de refactorizar".

## R6. Escaneo de secretos

- **Decision**: gitleaks v8.30.1. En CI, job con `actions/checkout` (`fetch-depth: 0`) y la imagen `ghcr.io/gitleaks/gitleaks:v8.30.1` (`gitleaks git`). Un `.gitleaksignore` registra el único falso positivo: el placeholder `JWT_SECRET=cambiame-...` de `.env.example` (commit `e672354`).
- **Rationale**: la imagen oficial evita depender de la licencia de `gitleaks-action` y fija la versión. Escaneo del repo nuevo verificado: 1 hallazgo, el placeholder.
- **Nota operativa**: en el clon local del autor, `git log --all` incluye las refs del remoto `upstream` (historial del equipo, con secretos). El objetivo local `make secrets` escanea solo la rama actual (`--log-opts=HEAD`).

## R7. Task runner

- **Decision**: `Makefile` en la raíz (convención CCDS v2) con objetivos `requirements`, `lint`, `format`, `test`, `secrets`, `smoke`, `up`, `down`, `clean`; el README incluye la tabla con el comando equivalente de cada objetivo para Windows sin `make`.

## R8. CI

- **Decision**:
  - `ci-python.yml`: job `lint` (ruff check + format --check) y job `test` en matriz por proyecto (`.`, `services/ml_api`, `services/routing_api`) con `astral-sh/setup-uv`.
  - `ci-secrets.yml`: gitleaks sobre el historial completo (workflow propio para que corra en cada push, cambie lo que cambie).
  - `ci-backend.yml`: solo jobs del Backend.
  - `ci-frontend.yml`: lint + build del Frontend (sale de `ci-backend.yml`).
- **Rationale**: un workflow por ecosistema hace más legible el estado en GitHub. FR-006.

## R9. Lint del Frontend

- **Decision**: eliminar la variable sin uso `heatmapCenter` en `apps/frontend/src/pages/EnRuta.jsx` (único error de ESLint).
- **Rationale**: es código muerto (el heatmap usa un centro fijo); quitarla no cambia el comportamiento. FR-010 prohíbe desactivar la regla.
