# Research: Contrato y módulo único de features

## R1. Qué variables entran

- **Decision**: las 9 variables pronosticadas del dataset (spec 003) y el instante objetivo; 13 features (ver [contracts/features.v1.md](contracts/features.v1.md)).
- **Rationale**: todas existen en el histórico y en vivo con 0 % de nulos y las mismas unidades (verificado en la spec 003, research R1), así que cumplen FR-007. La precipitación pronosticada es el baseline natural del modelo (*Model Output Statistics*): el modelo aprende a corregirla con el resto de variables.
- **Descartadas**:
  - `precip_lag_1h_mm` (lluvia observada de la hora anterior): no hay una fuente en tiempo real equivalente a la de entrenamiento (H-05). Era la feature dominante del modelo anterior (61 % de importancia), y en producción llegaba en 0.
  - `precipitation_probability`: no existe en el histórico.
  - Estación, latitud y longitud: invitarían a memorizar las 5 celdas de la etiqueta (Clarifications).
  - `dew_point_2m` crudo: casi colineal con temperatura y humedad; se usa la depresión del punto de rocío, más interpretable como "cercanía a la saturación".

## R2. Transformaciones

- **Codificación cíclica de hora y mes**: evita la discontinuidad 23 h → 0 h y diciembre → enero; se conserva del modelo original, pero ahora en hora local derivada de UTC (corrige H-06). El mes se centra en `mes − 1` para que enero sea el ángulo 0.
- **Componentes del viento**: la dirección en grados es circular (0° = 360°); las componentes u/v son continuas y valen 0 en calma. Convención meteorológica: la dirección indica de dónde viene el viento.
- **`log1p` en precipitación y CAPE**: ambas tienen distribuciones muy sesgadas, con muchos ceros (precipitación media 0.28 mm/h, máximo 16.4; CAPE media 202, máximo 2 950 en el dataset). La transformación estabiliza modelos lineales (baseline logístico) sin afectar a los de árboles.
- **Sin escalado en este módulo**: el escalado depende del modelo y vive en el pipeline de entrenamiento (spec 005); así el módulo de features no tiene estado y no requiere ajustarse a los datos.

## R3. Zona horaria

- **Decision**: `zoneinfo.ZoneInfo("America/Bogota")` de la stdlib.
- **Rationale**: Colombia no tiene horario de verano; usar el nombre IANA documenta la intención y es robusto ante cambios.

## R4. Validación de entradas

- **Decision**: `validate_inputs(df)` reutiliza los rangos de `mdva.data_contract` y lanza `FeatureInputError(campo, regla)` con el primer defecto por campo, reuniendo todos los defectos en el mensaje.
- **Rationale**: una sola definición de rangos para datos y entradas (sin duplicar números). La unidad no se puede verificar con rangos (Clarifications); la garantiza la fuente.
- **Alternatives considered**: Pydantic en el paquete `mdva` (dependencia nueva; el ML API sí lo usa y construirá su esquema HTTP a partir de este contrato en la spec 006).

## R5. Paridad entrenamiento/inferencia

- **Decision**: la prueba toma filas del dataset y las convierte en registros tipo petición (lista de diccionarios con `time_utc` como texto ISO 8601 con `Z`, igual que llegarían por HTTP). Compara `build_features` aplicado al DataFrame del dataset contra `build_features` aplicado a esos registros. Se corre con datos sintéticos en CI y con el dataset real si está disponible localmente.
- **Rationale**: la paridad no se rompe por la función en sí, sino por la conversión de tipos (texto ↔ timestamp, enteros ↔ flotantes) en el camino de inferencia.

## R6. Documentación sincronizada

- **Decision**: `docs/features.md` con una tabla cuyas filas siguen el orden de `FEATURES`; un test compara los nombres en orden.
