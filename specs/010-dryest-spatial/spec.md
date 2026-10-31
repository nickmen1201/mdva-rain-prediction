# Feature Specification: Ruta `dryest` espacial real

**Feature Branch**: `010-dryest-spatial` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Implemented (2026-10-31)

**Input**: User description: "Spec 010 (charter R-26, R-27; H-09): hacer real la ruta `dryest`. La penalización por lluvia debe variar por arista, interpolando a cada arista la probabilidad de una grilla espacial de predicciones del modelo, con costo tiempo × (1 + sensibilidad × p_lluvia(arista)). Un test con una grilla no uniforme debe demostrar que dryest ≠ fastest. Decidir sobre las elevaciones para bicicleta."

## Clarifications

### Session 2026-10-31

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿De dónde sale la grilla de probabilidades? → A: Del mismo modelo y la misma fuente que el resto del sistema: Open-Meteo para una malla regular sobre la caja que contiene el origen y el destino (con margen), en **una** consulta multi-ubicación, y una sola llamada por lotes al ML API (como el heatmap, spec 007). Nada se interpola desde datos inventados.
- Q: ¿Qué resolución? → A: 5 × 5 puntos sobre la caja del viaje (25 predicciones, mínimo 0.02° entre puntos): más fino que eso no agrega información, porque la fuente meteorológica tiene una resolución de varios kilómetros (documentado como limitación).
- Q: ¿Cómo se interpola a cada arista? → A: Interpolación bilineal sobre la malla regular, evaluada en el punto medio de la arista; fuera de la malla, el valor del borde más cercano.
- Q: ¿Qué sensibilidad? → A: `rain_sensitivity = 3.0` (valor ya documentado en el proyecto); costo `travel_time × (1 + 3 × p)`. Con p uniforme el costo es proporcional al de `fastest` y `dryest` coincide con `fastest` (resultado correcto, no un defecto).
- Q: ¿Cuándo se calcula `dryest`? → A: Solo si la probabilidad máxima de la grilla es ≥ 0.10 (comportamiento documentado en CLAUDE.md) y la señal está disponible; si no, no se ofrece y la respuesta lo dice.
- Q: ¿Elevaciones reales para la pendiente en bicicleta (R-27)? → A: No. Requiere un DEM y una dependencia de rasterización pesada solo para un factor heurístico sin evaluar; el charter permite eliminar el factor (ya se eliminó en la spec 009). Se documenta como decisión.
- Q: ¿La alternativa que ofrece el Backend debe ser la más seca? → A: Sí: el Backend pide `dryest` como alternativa y la muestra solo si su geometría difiere de la principal; el tipo (`dryest`) se informa en la respuesta (el Frontend la rotula en la spec 011).

## User Scenarios & Testing *(mandatory)*

Usuarios: **la persona que planifica** un viaje con lluvia probable y **quien revisa** (la ruta "más seca" deja de ser un nombre sin efecto, H-09).

### User Story 1 - Ruta más seca que realmente evita la lluvia (Priority: P1)

Cuando la lluvia es probable en parte del recorrido, la persona puede elegir una ruta que pasa por zonas con menor probabilidad de lluvia, aunque tarde un poco más.

**Why this priority**: hoy `dryest` multiplica todas las aristas por el mismo escalar y siempre coincide con `fastest` (H-09).

**Independent Test**: en un grafo con dos caminos y una grilla con lluvia alta solo sobre uno de ellos, `dryest` toma el camino seco y `fastest` el rápido.

**Acceptance Scenarios**:

1. **Given** una grilla no uniforme (p = 0.9 sobre el camino rápido, 0.05 sobre el alterno), **When** se pide la ruta, **Then** `dryest` ≠ `fastest`, y la probabilidad media de lluvia a lo largo de `dryest` es menor.
2. **Given** una grilla uniforme, **When** se pide la ruta, **Then** `dryest` coincide con `fastest` y no se ofrece como alternativa distinta.
3. **Given** la probabilidad máxima de la grilla < 0.10 o la señal no disponible, **When** se pide la ruta, **Then** no se calcula `dryest` y la respuesta lo indica.

---

### User Story 2 - Exposición a la lluvia informada (Priority: P2)

Cada ruta informa la probabilidad media de lluvia a lo largo del recorrido (ponderada por tiempo), para que la persona compare.

**Independent Test**: calcular la exposición de una ruta sobre una grilla conocida.

**Acceptance Scenarios**:

1. **Given** una ruta y una grilla, **When** se responde, **Then** cada opción trae `rain_exposure` ∈ [0, 1] = Σ p(arista) · t(arista) / Σ t(arista).

---

### User Story 3 - El Backend ofrece la ruta más seca como alternativa (Priority: P2)

**Acceptance Scenarios**:

1. **Given** lluvia probable y una ruta más seca distinta, **When** se planifica, **Then** el viaje trae la alternativa de tipo `dryest` con su tiempo.

### Edge Cases

- Origen y destino muy cercanos: la caja se amplía al mínimo de 0.02° por lado.
- Open-Meteo devuelve menos ubicaciones que las pedidas: la grilla no está disponible (no se rellena).
- Arista con nodos fuera de la caja: valor del borde más cercano.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El routing service MUST construir una grilla 5 × 5 de probabilidades del modelo sobre la caja del viaje con una consulta a Open-Meteo y una al ML API por lotes.
- **FR-002**: `dryest` MUST minimizar Σ t(arista) · (1 + 3 · p(arista)), con p interpolada bilinealmente en el punto medio de la arista.
- **FR-003**: Un test con grilla no uniforme MUST demostrar `dryest` ≠ `fastest` y menor exposición; con grilla uniforme MUST coincidir.
- **FR-004**: `dryest` MUST calcularse solo si la grilla está disponible y su máximo es ≥ 0.10.
- **FR-005**: Toda opción de ruta MUST informar `rain_exposure` cuando hay grilla, o `null`.
- **FR-006**: Las grillas MUST cachearse 5 min por caja redondeada.
- **FR-007**: El Backend MUST pedir la alternativa `dryest` y exponerla con su tipo cuando difiere de la principal.
- **FR-008**: La decisión sobre elevaciones (R-27) MUST quedar documentada; no se agrega factor de pendiente.

### Key Entities

- **Grilla de lluvia**: malla regular (lat, lon) → probabilidad, instante UTC, versión del modelo.
- **Exposición de una ruta**: probabilidad media ponderada por tiempo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El test de grilla no uniforme pasa: `dryest` ≠ `fastest` con exposición al menos 50 % menor en el caso sintético.
- **SC-002**: Una ruta con `dryest` hace exactamente 1 llamada a Open-Meteo y 1 al ML API para la grilla.
- **SC-003**: En el stack, una ruta urbana con `dryest` responde en < 5 s con el grafo cargado.

## Assumptions

- La variación espacial de la fuente meteorológica dentro del valle es real pero modesta (varios km por celda); el beneficio de `dryest` es mayor en recorridos largos que cruzan celdas.
