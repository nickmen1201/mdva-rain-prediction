# Implementation Plan: ML API v2 (contract-first) con el nuevo modelo

**Branch**: `006-ml-api-v2` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

## Summary

Contrato [openapi-v2.yaml](contracts/openapi-v2.yaml) escrito y validado primero. El servicio agrega un router `/v2` que carga `rain_classifier` 1.0.0 con `mdva.modeling.predict.load_model` en el `lifespan`, valida con el contrato de features de `mdva`, responde Problem Details y expone predicción individual, por lotes y monitoreo. Las reglas de monitoreo pasan a una función pura usada por v1 y v2. v1 no cambia de comportamiento.

## Technical Context

**Language/Version**: Python 3.11 (`services/ml_api`)

**Primary Dependencies**: FastAPI 0.115.6, Pydantic 2.10.3 (sin cambios); nuevo: paquete `mdva` como dependencia local (ruta), que trae pandas 3.1.0. Dev: `openapi-spec-validator` (valida el contrato; la stdlib no valida OpenAPI) y `pyyaml` (lee el contrato).

**Storage**: `models/rain_classifier/1.0.0/` (lectura)

**Testing**: pytest + TestClient: contrato vs. `app.openapi()`, tabla RF-17 (función pura y endpoint), casos inválidos, carga incompatible; los 29 de caracterización v1

**Target Platform**: contenedor `mdva-ml` (contexto raíz)

**Project Type**: servicio web

**Performance Goals**: lote de 81 registros < 1 s (SC-004)

**Constraints**: cambio aditivo; v1 intacto

## Packaging de `mdva`

Para no instalar matplotlib, pyarrow ni requests en la imagen del servicio, `mdva` declara como dependencias base solo lo que usa la predicción (numpy, pandas, scikit-learn, joblib), y el resto como extra `pipeline`. La raíz se instala con `uv sync --all-extras`; el servicio, con `mdva` sin extras.

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| IV. Contract-first | Contrato antes del código, validado con `openapi-spec-validator`; test de contrato contra el servicio; cambio clasificado como aditivo. | ✅ |
| Errores RFC 7807 | Handlers de v2 con `application/problem+json`. | ✅ |
| VI. Paridad train/serve | El servicio usa `mdva.features` y `mdva.modeling.predict`; sin features propias. | ✅ |
| VII. Sin datos fabricados | Entradas inválidas → 422; sin valores por defecto para variables. | ✅ |
| II. Reproducible | Dependencias fijadas en `uv.lock`; verificación de versiones al cargar. | ✅ |

## Project Structure

```text
specs/006-ml-api-v2/{spec.md, plan.md, research.md, quickstart.md, tasks.md, contracts/openapi-v2.yaml}
pyproject.toml                         # mdva: dependencias base + extra pipeline
services/ml_api/
├── main.py            # app v1 (sin cambios de comportamiento) + include_router(v2) + lifespan
├── v2.py              # router, esquemas generados desde mdva, Problem Details
├── monitoring.py      # reglas RF-17 como función pura
├── pyproject.toml / uv.lock / Dockerfile
└── tests/{test_contract.py, test_v2.py, test_monitoring_rules.py}
.dockerignore          # + mdva/, pyproject.toml, README.md
tests/e2e/smoke_stack.py   # + verificaciones v2
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Dos versiones de API conviviendo | El Backend consume v1 hasta la spec 007 | Reemplazar v1 rompería el producto entre specs (charter §4) |
