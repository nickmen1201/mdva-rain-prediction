# Feature Specification: ML API v2 (contract-first) con el nuevo modelo

**Feature Branch**: `006-ml-api-v2` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Implemented (2026-10-29)

**Input**: User description: "Servir el modelo de la spec 005 desde el servicio de predicción con un contrato OpenAPI escrito antes del código, validación con el contrato de features, errores Problem Details, carga del modelo al arrancar y reglas de monitoreo extraídas y probadas, sin romper a los consumidores actuales (charter R-19–R-24; constitución IV)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Se reemplazan los endpoints actuales o se agregan nuevos? → A: Se agregan bajo `/v2` (cambio aditivo). Los endpoints actuales (`/predecir/*`, `/monitorear/trayecto`) siguen funcionando igual hasta que el Backend migre (spec 007); allí se retiran junto con los modelos antiguos.
- Q: ¿Cómo pide el Backend predicciones para muchos puntos u horas (heatmap de 81 puntos, pronóstico de 6 horas)? → A: Con un endpoint por lotes en v2 (hasta 200 registros por petición), además del individual.
- Q: ¿Qué responde v2 cuando la entrada es inválida? → A: 422 con Problem Details (RFC 7807) que lista cada campo y regla; nunca una predicción con valores rellenados.
- Q: ¿Las reglas de monitoreo de trayecto cambian? → A: No (charter RF-17). Solo se extraen a una función pura y se exige que el instante del dato meteorológico tenga zona horaria (en v1, un instante sin zona se trataba en silencio como latencia 0).

## User Scenarios & Testing *(mandatory)*

Usuarios: **el Backend** (consumidor del servicio), **quien desarrolla** y **quien revisa** el portafolio.

### User Story 1 - Predicción con el nuevo modelo y entradas validadas (Priority: P1)

El Backend envía el instante UTC y las 9 variables del pronóstico de un punto y recibe la probabilidad de lluvia, el nivel de alerta y la versión del modelo. Una entrada inválida recibe un error que nombra el campo.

**Why this priority**: es el camino por el que el modelo nuevo llega al producto.

**Independent Test**: llamar al endpoint con una entrada válida y con entradas inválidas; contrastar contra el contrato.

**Acceptance Scenarios**:

1. **Given** el servicio arriba, **When** se envía una entrada válida, **Then** responde 200 con probabilidad en [0, 1], nivel VERDE/AMARILLO/ROJO según 0.40/0.70 y la versión del modelo.
2. **Given** una entrada con un campo faltante, fuera de rango o un instante sin zona horaria, **When** se envía, **Then** responde 422 Problem Details con cada campo y regla.
3. **Given** un lote de 81 registros, **When** se envía al endpoint por lotes, **Then** responde una predicción por registro, en el mismo orden.

---

### User Story 2 - El contrato manda (Priority: P1)

Existe un contrato OpenAPI versionado y validado; ningún endpoint v2 existe en el código sin estar en el contrato, y una prueba lo verifica contra el servicio en ejecución.

**Why this priority**: constitución IV (contract-first).

**Independent Test**: validar el archivo de contrato con un linter de OpenAPI y comparar sus rutas y esquemas con los que publica el servicio.

**Acceptance Scenarios**:

1. **Given** el contrato, **When** se valida, **Then** es un OpenAPI 3.1 válido.
2. **Given** el servicio, **When** se comparan sus rutas v2, métodos, campos requeridos de entrada y campos de salida con el contrato, **Then** coinciden.

---

### User Story 3 - Monitoreo de trayecto con el nuevo modelo (Priority: P2)

El Backend envía la probabilidad al inicio del viaje, el instante del dato meteorológico y las condiciones actuales, y recibe el nivel de cambio con las mismas reglas de hoy.

**Why this priority**: preserva RF-17 al migrar al modelo nuevo.

**Independent Test**: la misma tabla de casos de la spec 002 aplicada a la función pura y al endpoint v2.

**Acceptance Scenarios**:

1. **Given** la tabla de reglas de RF-17, **When** se evalúa con la función pura y con el endpoint v2, **Then** todos los casos dan el nivel esperado.

---

### User Story 4 - Arranque y salud verificables (Priority: P2)

El servicio carga los modelos al arrancar (no al importar), informa en su health la versión del modelo y si está listo, y no arranca si el modelo es incompatible con el entorno.

**Why this priority**: hoy un modelo con otra versión de scikit-learn se carga con una advertencia y puede dar resultados inválidos (H-13).

**Independent Test**: health con el modelo correcto; arranque con un modelo incompatible.

**Acceptance Scenarios**:

1. **Given** el modelo correcto, **When** se consulta health, **Then** responde `ready: true` con nombre y versión del modelo.
2. **Given** un modelo incompatible, **When** arranca el servicio, **Then** falla con un mensaje que explica la incompatibilidad.

### Edge Cases

- Lote vacío o de más de 200 registros: 422.
- Errores internos inesperados: 500 Problem Details con un identificador de error y sin detalles internos.
- El comportamiento de v1 no cambia: los tests de caracterización de la spec 002 siguen pasando.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El contrato OpenAPI de v2 MUST existir, validarse y preceder al código; una prueba MUST comparar el servicio con el contrato.
- **FR-002**: v2 MUST exponer health, predicción individual, predicción por lotes y monitoreo de trayecto.
- **FR-003**: Las entradas de predicción MUST ser las del contrato de features (spec 004) y validarse con él.
- **FR-004**: Las respuestas de predicción MUST incluir probabilidad, nivel de alerta y versión del modelo.
- **FR-005**: Los errores de v2 MUST usar Problem Details (RFC 7807) sin exponer detalles internos.
- **FR-006**: Los modelos MUST cargarse al arrancar; un modelo incompatible MUST impedir el arranque.
- **FR-007**: Las reglas de monitoreo MUST ser una función pura con la tabla de RF-17 probada; v2 MUST exigir instantes con zona horaria.
- **FR-008**: Los endpoints v1 y su comportamiento MUST mantenerse sin cambios (pruebas de caracterización en verde).
- **FR-009**: El servicio MUST reutilizar el paquete `mdva` (features y carga del modelo) sin duplicar su lógica.

### Key Entities

- **Petición de predicción**: instante UTC + 9 variables (spec 004).
- **Predicción**: probabilidad, nivel de alerta, versión del modelo.
- **Petición de monitoreo**: probabilidad inicial, instante del dato meteorológico, condiciones actuales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El contrato valida como OpenAPI 3.1 y las rutas, métodos, campos de entrada requeridos y campos de salida de v2 coinciden al 100 % con el servicio.
- **SC-002**: El 100 % de las filas de la tabla RF-17 pasan en la función pura y en el endpoint v2.
- **SC-003**: Los 29 tests de caracterización de v1 siguen en verde.
- **SC-004**: Un lote de 81 registros responde en menos de 1 s en el contenedor.
- **SC-005**: El smoke test del stack es idéntico a la línea base más las verificaciones nuevas de v2 en verde.

## Assumptions

- El modelo servido es `rain_classifier` 1.0.0 (spec 005).
- El Backend sigue usando v1 hasta la spec 007.
- Fuera de alcance: autenticación entre servicios (red interna de Docker), métricas de observabilidad.
