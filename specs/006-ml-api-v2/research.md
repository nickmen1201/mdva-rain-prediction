# Research: ML API v2

## R1. Convivencia v1/v2

- **Decision**: router `/v2` en el mismo servicio y el mismo puerto; v1 sin cambios hasta la spec 007.
- **Rationale**: el Backend consume v1; un cambio aditivo permite migrar el consumidor en su propia spec, con el smoke test en verde en cada paso.

## R2. Esquemas generados desde `mdva`

- **Decision**: el modelo Pydantic de entrada se genera con `pydantic.create_model` a partir de `mdva.features.RAW_INPUTS` (rango → `ge`/`le`, unidad → `description`) y `AwareDatetime` para `time_utc`.
- **Rationale**: una sola fuente de verdad de rangos (contrato de datos de la spec 003). El contrato OpenAPI se escribe a mano (contract-first) y el test verifica que el esquema generado coincide con él.

## R3. Problem Details

- **Decision**: excepciones de validación en rutas `/v2` → 422 `application/problem+json` con `errors: [{field, rule}]`; errores inesperados → 500 con `detail` genérico e `instance` = identificador aleatorio que también se registra en el log. Las rutas v1 conservan los handlers por defecto de FastAPI.

## R4. Lotes

- **Decision**: hasta 200 registros por petición (cubre la grilla de 81 puntos y 24 h de pronóstico horario). Una sola llamada a `predict_proba` vectorizada.

## R5. Carga del modelo

- **Decision**: `lifespan` llama a `load_model(version, models_dir)` con `MDVA_MODEL_VERSION` (por defecto `1.0.0`) y `MDVA_MODELS_DIR`. Si falla (versión de scikit-learn o contrato de features), el servicio no arranca.
- **Nota**: `mdva` se instala como paquete no editable dentro de la imagen, así que `mdva.config.MODELS_DIR` apuntaría a `site-packages`; por eso el servicio siempre pasa `models_dir` explícito.

## R6. Validador de OpenAPI

- **Decision**: `openapi-spec-validator` (dev) valida el YAML como OpenAPI 3.1 en un test.
- **Alternatives considered**: Spectral (requiere Node en el entorno de Python).
