# Feature Specification: Backend — clima con Open-Meteo y modelo v2

**Feature Branch**: `007-backend-weather-openmeteo` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Implemented (2026-10-29)

**Input**: User description: "Quitar Google Weather del Backend (proyecto sin facturación, H-19): condiciones actuales, pronóstico horario, heatmap y monitoreo deben obtener el clima de Open-Meteo —la misma fuente con que se entrenó el modelo— y predecir con el ML API v2, con zonas horarias explícitas (charter R-34–R-36, R-35; H-04, H-06)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Qué hora del pronóstico se usa como "condiciones actuales"? → A: La hora UTC en curso (la hora truncada) del pronóstico de Open-Meteo para el punto; su instante se informa como "instante del dato meteorológico".
- Q: ¿Se conserva la mezcla 65 % modelo + 35 % probabilidad de Google (hallazgo H-21)? → A: No. Era una combinación no documentada ni evaluada; la probabilidad mostrada pasa a ser la del modelo evaluado en la spec 005.
- Q: ¿Qué pasa si falla la predicción de un punto del heatmap (hoy devuelve 0 %, hallazgo H-22)? → A: La petición del heatmap falla con un error explícito; nunca se devuelve una probabilidad inventada (constitución VII).
- Q: ¿Se implementa "precipitación activa > 0.1 mm fuerza llueve" (charter RF-11)? → A: No: al revisar el código se verificó que esa regla no existe hoy (solo aparece en documentación desactualizada); agregarla sería comportamiento nuevo. Se corrige el charter en la spec 012.
- Q: ¿Qué muestra la interfaz en lugar de la probabilidad de la regresión logística (el modelo v2 no la entrega)? → A: Se retira esa tarjeta y la probabilidad del modelo se rotula "Probabilidad de lluvia"; mostrar 0 % sería un dato fabricado.
- Q: ¿Se retiran ya los endpoints v1 del ML API? → A: No: el routing service todavía los usa; se retiran en la spec 009, cuando migre.

## User Scenarios & Testing *(mandatory)*

Usuarios: **la persona que usa la app** (planifica viajes y consulta el clima) y **quien revisa** el portafolio (paridad entrenamiento/producción).

### User Story 1 - Ver el clima y la probabilidad de lluvia actuales (Priority: P1)

La persona consulta el clima en un punto y ve temperatura, humedad, nubosidad, viento y la probabilidad de lluvia del modelo, sin depender de servicios de pago.

**Why this priority**: hoy responde error 502 porque Google Weather no tiene facturación (H-19); bloquea clima actual, planificación y monitoreo.

**Independent Test**: consultar el clima actual de un punto del valle y obtener una respuesta completa.

**Acceptance Scenarios**:

1. **Given** el stack arriba sin ninguna API key de clima, **When** se consulta el clima actual de Medellín, **Then** responde 200 con variables meteorológicas, probabilidad en [0, 1] e instante UTC del dato.
2. **Given** dos consultas del mismo punto dentro de 3 minutos, **When** se hacen, **Then** la segunda no vuelve a llamar a las fuentes externas.

---

### User Story 2 - Pronóstico horario y heatmap coherentes con el modelo (Priority: P1)

El pronóstico de las próximas horas y el mapa de calor usan la misma fuente y el mismo modelo que el clima actual, con horas correctas en hora local.

**Why this priority**: hoy cada hora del pronóstico hace una llamada al modelo con features distintas a las de entrenamiento, y el heatmap llama a Google por cada uno de los 81 puntos.

**Independent Test**: pedir 6 horas de pronóstico y una grilla de 81 puntos; revisar horas, probabilidades y número de llamadas externas.

**Acceptance Scenarios**:

1. **Given** una ubicación, **When** se piden 6 horas, **Then** se devuelven 6 horas consecutivas desde la hora en curso, con hora local de Bogotá y probabilidad por hora.
2. **Given** una grilla de 81 puntos, **When** se pide el heatmap, **Then** se devuelve una probabilidad por punto usando una sola consulta de clima y una sola de predicción.
3. **Given** que la fuente de clima falla, **When** se pide el heatmap, **Then** responde un error explícito y no probabilidades en 0.

---

### User Story 3 - Monitoreo de trayecto con el dato real (Priority: P2)

Durante un viaje, el sistema compara la probabilidad del inicio con la actual usando el instante real del dato meteorológico, y genera alertas con las mismas reglas.

**Why this priority**: hoy el instante del dato se reemplaza por "ahora" al planificar, y la hora enviada al modelo dependía de la zona horaria del contenedor (H-06).

**Independent Test**: monitorear un viaje con un snapshot conocido y verificar el nivel y la latencia.

**Acceptance Scenarios**:

1. **Given** un viaje planificado, **When** se guarda su snapshot, **Then** el instante del dato meteorológico es el de la hora del pronóstico usada.
2. **Given** una posición durante el viaje, **When** se monitorea, **Then** el nivel de cambio sigue la tabla RF-17 calculada por el servicio de predicción.

---

### User Story 4 - La interfaz no muestra datos inexistentes (Priority: P3)

La tarjeta de predicción muestra una sola probabilidad de lluvia, rotulada como tal, sin la del modelo retirado.

**Independent Test**: abrir el resultado de un viaje y revisar la tarjeta.

**Acceptance Scenarios**:

1. **Given** una predicción sin probabilidad de regresión logística, **When** se muestra la tarjeta, **Then** no aparece "Reg. Logística: 0 %".

### Edge Cases

- La hora en curso no aparece en la respuesta de la fuente (desfase de reloj): se usa la hora más cercana no anterior y se registra.
- La fuente declara unidades distintas a las pedidas: la petición falla (nunca se convierten en silencio).
- El servicio de predicción rechaza una entrada (422): el Backend responde un error explícito, no una probabilidad por defecto.
- Más de 81 puntos en la grilla: 400 (comportamiento actual).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Backend MUST obtener las 9 variables del contrato de features de Open-Meteo, pidiendo unidades explícitas y UTC, y MUST verificar las unidades declaradas.
- **FR-002**: El Backend MUST predecir con el ML API v2 (individual o por lotes), enviando el instante UTC del dato.
- **FR-003**: El Backend MUST NOT llamar a Google Weather ni requerir una API key de clima.
- **FR-004**: Clima actual, pronóstico horario, heatmap y monitoreo MUST usar la misma fuente y el mismo modelo.
- **FR-005**: El heatmap MUST resolverse con una consulta de clima y una de predicción para toda la grilla (≤ 81 puntos), conservando el TTL de 180 s (charter RF-18).
- **FR-006**: La predicción puntual MUST conservar la caché de 180 s (charter RF-19).
- **FR-007**: Ningún error de clima o predicción MUST traducirse en una probabilidad inventada.
- **FR-008**: El snapshot del viaje MUST guardar el instante real del dato meteorológico, y el monitoreo MUST usar el endpoint v2 con ese instante.
- **FR-009**: Las horas mostradas MUST estar en hora local de Bogotá derivada de instantes UTC, independientemente de la zona horaria del servidor.
- **FR-010**: La interfaz MUST dejar de mostrar la probabilidad del modelo retirado.
- **FR-011**: Los contratos externos del Backend (rutas, campos existentes de las respuestas) MUST mantenerse; solo se agregan campos.

### Key Entities

- **Entrada horaria del modelo**: instante UTC + 9 variables con unidades del contrato.
- **Predicción de lluvia (respuesta existente)**: probabilidad y variables, más el instante UTC del dato (campo nuevo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clima actual y pronóstico horario responden 200 en el smoke test (el clima actual daba 502).
- **SC-002**: Un heatmap de 81 puntos hace exactamente 1 llamada de clima y 1 de predicción, y responde en menos de 3 s.
- **SC-003**: 0 referencias a Google Weather en el código del Backend.
- **SC-004**: Los tests del Backend pasan (los existentes ajustados al nuevo flujo más los nuevos de clientes y servicio).
- **SC-005**: El resto del smoke test queda igual a la línea base (planificar sigue fallando por Google Directions hasta la spec 008).

## Assumptions

- Open-Meteo sigue siendo gratuito y sin API key.
- La planificación de viajes sigue dependiendo de Google Directions/Geocoding hasta la spec 008.
- Fuera de alcance: retirar los endpoints v1 del ML API (spec 009), cambios en el Frontend más allá de la tarjeta de predicción (spec 011).
