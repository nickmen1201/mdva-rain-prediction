# Contract: comandos del desarrollador y checks de CI

## Objetivos del Makefile (raíz)

| Objetivo | Comando equivalente (Windows sin `make`) | Resultado esperado |
|---|---|---|
| `make requirements` | `uv sync` · `uv sync --project services/ml_api` · `uv sync --project services/routing_api` | 3 entornos `.venv` con versiones del lock |
| `make lint` | `uv run ruff check .` · `uv run ruff format --check .` | código 0 sin hallazgos |
| `make format` | `uv run ruff check --fix .` · `uv run ruff format .` | archivos formateados |
| `make test` | `uv run pytest` · `uv run --project services/ml_api pytest services/ml_api/tests` · `uv run --project services/routing_api pytest services/routing_api/tests` | todos los tests en verde |
| `make secrets` | `docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.30.1 git /repo --log-opts=HEAD` | `no leaks found` |
| `make up` / `make down` | `docker compose -f docker-compose.dev.yml up --build -d` / `... down` | stack arriba / abajo |
| `make smoke` | `uv run python tests/e2e/smoke_stack.py` | JSON igual a la línea base |
| `make clean` | borrar `__pycache__`, `.pytest_cache`, `.ruff_cache` | — |

## Checks de CI

| Workflow | Job | Falla si |
|---|---|---|
| `ci-python.yml` | `lint` | ruff encuentra un hallazgo o un archivo sin formato |
| `ci-python.yml` | `test (., services/ml_api, services/routing_api)` | algún test falla o el lock no corresponde al `pyproject.toml` |
| `ci-secrets.yml` | `gitleaks` | gitleaks reporta un hallazgo no listado en `.gitleaksignore` |
| `ci-backend.yml` | `build`, `compile-check` | igual que hoy |
| `ci-frontend.yml` | `frontend` | ESLint con errores o build fallido |

Clasificación: **aditivo** (no cambia endpoints ni el comportamiento de los servicios).
