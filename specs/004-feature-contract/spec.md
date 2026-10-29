# Feature Specification: Contrato y módulo único de features

**Feature Branch**: `004-feature-contract` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Una sola definición de features compartida por entrenamiento e inferencia, con contrato de entradas explícito (unidades, rangos, zona horaria) y prueba de paridad, para eliminar el train/serve skew (charter R-07–R-10; H-03, H-05, H-06; constitución VI)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Se separan dos modelos (nowcast con lluvia observada de la hora anterior y forecast sin ella), como proponía el charter R-09? → A: No. Con el dataset de la spec 003 no existe lluvia observada en tiempo real equivalente a la de entrenamiento, así que la feature de lluvia rezagada se elimina y un único conjunto de features sirve para la hora actual y las siguientes (las variables son las pronosticadas para la hora objetivo). Se cumple la regla de no rellenar con ceros una feature desconocida.
- Q: ¿Cómo llega la hora al modelo? → A: Como instante UTC con zona explícita; la hora y el mes locales de Bogotá se derivan dentro del módulo de features (constitución: timestamps en UTC, hora local solo como feature). Esto elimina el desfase de 5 h de H-06.
- Q: ¿Puede un chequeo de rango detectar viento en km/h (charter R-10)? → A: No de forma fiable: los valores típicos en km/h (5–30) caben en un rango válido en m/s. Las unidades se garantizan con nombres de campo que llevan la unidad y verificando la unidad declarada por la fuente (spec 003); el rango solo descarta valores físicamente imposibles.
- Q: ¿Se incluyen coordenadas o la estación como features? → A: No. Las 13 estaciones caen en 5 celdas de la etiqueta; usar la ubicación invitaría a memorizar celdas y el modelo debe servir para cualquier punto del valle (heatmap). La variación espacial entra por las variables pronosticadas en cada punto.

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien desarrolla** el modelo y los servicios, y **quien revisa** el portafolio buscando señales de train/serve skew.

### User Story 1 - Las mismas features en entrenamiento y en producción (Priority: P1)

Las features que ve el modelo al entrenar y las que recibe al predecir se calculan con el mismo código a partir de las mismas variables crudas, y una prueba automática lo demuestra.

**Why this priority**: los errores más graves del proyecto original eran de este tipo (viento en otra unidad, hora desplazada 5 h, una feature dominante que en producción llegaba en 0).

**Independent Test**: tomar filas del dataset de modelado, convertirlas al formato de una petición de predicción y comprobar que la matriz de features es idéntica por ambos caminos.

**Acceptance Scenarios**:

1. **Given** una fila del dataset de modelado, **When** se calculan sus features por el camino de entrenamiento y por el de inferencia, **Then** los valores y el orden de columnas son idénticos.
2. **Given** un instante UTC, **When** se calculan las features temporales, **Then** reflejan la hora local de Bogotá (UTC−5).

---

### User Story 2 - Entradas inválidas se rechazan con un mensaje claro (Priority: P1)

Una petición de predicción con un campo faltante, una hora sin zona horaria o un valor físicamente imposible se rechaza indicando el campo y la regla, en lugar de producir una predicción silenciosa.

**Why this priority**: hoy un timestamp sin zona horaria se trata en silencio como latencia 0, y nada impide enviar valores imposibles (constitución VII).

**Independent Test**: enviar al validador entradas con cada tipo de defecto y comprobar el error.

**Acceptance Scenarios**:

1. **Given** entradas con un campo faltante, un valor fuera de rango o un instante sin zona horaria, **When** se validan, **Then** se rechazan nombrando el campo y la regla.
2. **Given** entradas válidas en cualquier zona horaria explícita, **When** se validan, **Then** se aceptan y se normalizan a UTC.

---

### User Story 3 - El conjunto de features está documentado y justificado (Priority: P2)

Un revisor encuentra, en un solo lugar, cada feature con su origen, unidad, transformación y por qué está; y la lista de variables que se descartaron y por qué.

**Why this priority**: convierte decisiones implícitas en decisiones defendibles en una entrevista.

**Independent Test**: comparar la documentación con la lista de features del código (una prueba lo verifica).

**Acceptance Scenarios**:

1. **Given** la documentación de features, **When** se compara con la lista del código, **Then** coinciden exactamente en nombres y orden.

### Edge Cases

- Dirección del viento 0° y 360°: deben producir la misma feature (componentes del vector, no el ángulo).
- Viento en calma: dirección irrelevante; las componentes valen 0.
- Precipitación y energía convectiva muy sesgadas (muchos ceros): se transforman para reducir la influencia de extremos.
- Instantes con minutos distintos de cero: se usan tal cual para la hora local (la hora se trunca).
- Entradas con columnas extra: se ignoran sin error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Existe un único componente que transforma variables crudas en la matriz de features; entrenamiento e inferencia MUST usarlo, y ningún otro componente del sistema MUST recalcular features.
- **FR-002**: Las variables crudas aceptadas MUST ser las 9 variables pronosticadas del dataset (con la unidad en el nombre o en el contrato) más el instante UTC objetivo.
- **FR-003**: La hora y el mes MUST derivarse en hora local de Bogotá a partir del instante UTC, con codificación cíclica.
- **FR-004**: La dirección del viento MUST representarse como componentes del vector de viento.
- **FR-005**: El orden y los nombres de las features MUST ser fijos y versionados; el modelo entrenado MUST guardar la versión del contrato de features con la que se entrenó.
- **FR-006**: La validación de entradas MUST rechazar campos faltantes, valores nulos, valores fuera del rango físico y instantes sin zona horaria, nombrando el campo y la regla.
- **FR-007**: No MUST existir ninguna feature que no esté disponible en producción con la misma fuente y semántica que en entrenamiento.
- **FR-008**: Una prueba automática MUST demostrar la paridad entrenamiento/inferencia (US1).
- **FR-009**: La documentación de features MUST coincidir con el código (prueba automática).

### Key Entities

- **Entrada cruda**: instante UTC + 9 variables pronosticadas con unidad y rango.
- **Contrato de features**: versión, lista ordenada de features con origen y transformación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para 1 000 filas aleatorias del dataset, la matriz de features por el camino de entrenamiento y por el de inferencia es idéntica (diferencia máxima 0).
- **SC-002**: El 100 % de los casos de entrada inválida de la batería de pruebas se rechaza con un mensaje que nombra el campo.
- **SC-003**: 0 features dependen de información no disponible en producción (revisión documentada feature por feature).
- **SC-004**: La documentación lista el 100 % de las features del código, en el mismo orden.

## Assumptions

- La fuente de producción es el pronóstico de Open-Meteo con las mismas variables y unidades que el histórico (verificado en la spec 003).
- La adaptación de los servicios (ML API, Backend) al nuevo contrato de entradas es alcance de las specs 006 y 007; esta spec entrega el componente y su contrato.
- Fuera de alcance: selección de features con datos y entrenamiento (spec 005).
