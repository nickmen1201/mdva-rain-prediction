#################################################################################
# MDVA — objetivos del proyecto (Cookiecutter Data Science v2)
# En Windows sin `make`, ver la tabla de comandos equivalentes en el README.
#################################################################################

PYTHON_PROJECTS = . services/ml_api services/routing_api
COMPOSE = docker compose -f docker-compose.dev.yml
GITLEAKS_IMAGE = ghcr.io/gitleaks/gitleaks:v8.30.1

.PHONY: requirements lint format test secrets data validate-labels up down smoke clean help

## Instalar los entornos de los 3 proyectos Python desde sus lockfiles
requirements:
	@for p in $(PYTHON_PROJECTS); do uv sync --frozen --project $$p || exit 1; done

## Lint y chequeo de formato (ruff)
lint:
	uv run ruff check .
	uv run ruff format --check .

## Corregir lint automático y formatear (ruff)
format:
	uv run ruff check --fix .
	uv run ruff format .

## Tests de los 3 proyectos Python
test:
	uv run pytest
	uv run --project services/ml_api pytest services/ml_api/tests
	uv run --project services/routing_api pytest services/routing_api/tests

## Escaneo de secretos en el historial de la rama actual (gitleaks)
secrets:
	docker run --rm -v "$(CURDIR):/repo" $(GITLEAKS_IMAGE) git /repo --no-banner --redact --log-opts=HEAD

## Construir el dataset de modelado (descarga con caché + quality gates)
data:
	uv run python -m mdva.dataset

## Validar la etiqueta contra pluviómetros SIATA y calibrar el umbral
validate-labels:
	uv run python -m mdva.label_validation

## Levantar el stack de desarrollo
up:
	$(COMPOSE) up --build -d

## Bajar el stack de desarrollo
down:
	$(COMPOSE) down

## Smoke test de punta a punta (requiere `make up`)
smoke:
	uv run python tests/e2e/smoke_stack.py

## Borrar cachés de Python y herramientas
clean:
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" \) -not -path "./apps/*" -prune -exec rm -rf {} +

## Listar objetivos
help:
	@grep -B1 -E "^[a-z]+:" Makefile | grep -E "^## " | sed 's/## //'
