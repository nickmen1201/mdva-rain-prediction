# Feature Specification: Dataset reproducible de lluvia (Open-Meteo) con validación externa SIATA

**Feature Branch**: `003-openmeteo-dataset` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Los 185 CSV de SIATA se perdieron; construir con Open-Meteo un dataset de modelado reproducible desde cero, con contrato de datos y quality gates, y usar los CSV de SIATA disponibles solo para validar la etiqueta (charter R-01–R-06, H-02, H-04, H-20; constitución V)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates"); el autor delegó la elección de fuente ("usemos Open Meteo o cualquier otra opción que sirva").

- Q: ¿Qué representa la etiqueta "llueve"? → A: Precipitación horaria de reanálisis (ERA5) por encima de un umbral de "lluvia apreciable" en la ubicación y hora dadas. Es lo más cercano a una observación que existe gratis para todo el periodo. Un análisis previo (research R4) mostró que con 0.1 mm/h ERA5 marca lluvia en el 56 % de las horas frente al 19 % de los pluviómetros; el umbral se calibra con la primera mitad del mes de SIATA y la fidelidad se reporta con la segunda mitad (US3).
- Q: ¿En qué zona horaria están los datos de SIATA? → A: Hora local de Colombia (UTC−5), deducida del ciclo diurno de la lluvia (research R5); no se usa el desfase de máxima correlación porque está sesgado por el ciclo diurno adelantado del reanálisis.
- Q: ¿De dónde salen las variables meteorológicas de entrada? → A: De pronósticos archivados (los mismos que el sistema recibe en producción), para que entrenamiento e inferencia usen la misma fuente (charter R-05, constitución VI).
- Q: ¿Qué ubicaciones cubre el dataset? → A: Las 13 estaciones SIATA de los CSV disponibles, que cubren el Valle de Aburrá de Caldas a Barbosa y permiten cruzar la etiqueta con pluviómetros reales en el mismo punto.
- Q: ¿Qué periodo? → A: 2022-01-01 a 2025-12-31 (4 años completos). Antes de mediados de 2021 algunas variables de pronóstico archivado vienen vacías.
- Q: ¿Se usa el CSV "clean" de SIATA? → A: No; se parte del crudo y se documenta la limpieza propia, porque el "clean" conserva códigos de calidad anómalos y su procedencia no está documentada.

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien desarrolla o reproduce** el proyecto y **quien revisa** el portafolio (un evaluador técnico de Ciencia de Datos).

### User Story 1 - Reproducir el dataset desde cero con un comando (Priority: P1)

Desde un clon limpio y sin archivos previos, un comando descarga los datos crudos, los limpia y produce el dataset de modelado. Repetir el comando no vuelve a descargar lo ya descargado y produce exactamente el mismo resultado.

**Why this priority**: sin datos reproducibles no hay modelo defendible; hoy el entrenamiento depende de archivos que ya no existen (H-02, H-20).

**Independent Test**: borrar `data/`, ejecutar el comando, anotar la huella del dataset final; ejecutarlo de nuevo y comprobar 0 descargas nuevas y la misma huella.

**Acceptance Scenarios**:

1. **Given** un clon limpio con conexión a internet, **When** se ejecuta el comando de datos, **Then** se crea el dataset de modelado con una fila por ubicación y hora del periodo.
2. **Given** el dataset ya construido, **When** se ejecuta de nuevo el comando, **Then** no se descarga nada y el dataset resultante es idéntico byte a byte.
3. **Given** que la fuente responde con límite de tasa o error temporal, **When** corre el comando, **Then** reintenta con espera creciente y, si no se recupera, falla indicando qué pieza faltó, sin dejar archivos a medio escribir.

---

### User Story 2 - Los datos defectuosos detienen el pipeline (Priority: P1)

Cada etapa valida los datos contra un contrato explícito (columnas, tipos, unidades, rangos, zona horaria, unicidad, cobertura) y se detiene si algo no cumple, dejando un reporte de calidad legible.

**Why this priority**: constitución V; los errores de este proyecto (viento en km/h tratado como m/s, horas desplazadas) son exactamente los que un contrato habría detectado (H-03, H-06).

**Independent Test**: alterar un archivo intermedio (p. ej. una humedad de 150 % o una hora duplicada) y comprobar que la etapa siguiente falla con un mensaje que identifica la regla violada.

**Acceptance Scenarios**:

1. **Given** datos válidos, **When** corre el pipeline, **Then** se genera un reporte de calidad con conteos, nulos, cobertura por ubicación y resultado de cada regla.
2. **Given** un valor fuera de rango, una unidad distinta a la esperada, una fila duplicada o una hora faltante por encima del tolerado, **When** corre la validación, **Then** el pipeline se detiene y no promueve datos a la etapa siguiente.

---

### User Story 3 - Saber cuánto se parece la etiqueta a la lluvia real (Priority: P2)

Un revisor puede ver, con números, qué tan bien coincide la etiqueta del dataset con lo que midieron los pluviómetros de SIATA en las mismas ubicaciones y horas, y qué tan bien lo hace el pronóstico crudo de lluvia.

**Why this priority**: la etiqueta no es una observación directa; medir su fidelidad convierte una limitación en una decisión documentada (charter R-01).

**Independent Test**: ejecutar la validación externa y revisar el reporte: métricas de concordancia por estación y en conjunto, y el desfase horario que mejor alinea ambas series.

**Acceptance Scenarios**:

1. **Given** el CSV crudo de SIATA y el dataset, **When** se ejecuta la validación externa, **Then** se produce un reporte con, por estación y en total: horas comparadas, tasa de lluvia en cada fuente, precisión, sensibilidad, F1 y kappa de Cohen, para la etiqueta y para el pronóstico crudo.
2. **Given** que la zona horaria de los datos de SIATA no está documentada, **When** corre la validación, **Then** el reporte incluye la concordancia para cada desfase de −8 h a +8 h y el ciclo diurno de cada fuente, y el pipeline usa el desfase justificado en el plan (UTC−5).
3. **Given** la calibración del umbral, **When** se elige, **Then** se usa solo la primera mitad del periodo de SIATA y las métricas reportadas salen de la segunda mitad.

### Edge Cases

- La fuente devuelve un valor nulo aislado: se tolera hasta un umbral por variable y ubicación; por encima, la validación falla.
- Una descarga se interrumpe: el archivo crudo incompleto no debe quedar en `data/raw/` (escritura atómica).
- Varias estaciones caen en la misma celda de reanálisis: se registra cuántas ubicaciones comparten celda (limita la resolución espacial de la etiqueta).
- Horas de SIATA con pocos minutos válidos: no se usan para validar (umbral de cobertura por hora).
- Lecturas de SIATA con calidad distinta de 1 o precipitación negativa: se descartan y se cuentan en el reporte.
- Cambio de horario: no aplica en Colombia, pero todo se guarda en UTC con zona explícita.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Un único comando MUST producir el dataset de modelado desde cero (descarga, limpieza, unión, etiqueta).
- **FR-002**: Las descargas MUST guardarse sin modificar en `data/raw/` y no volver a descargarse si ya existen y son íntegras; `data/raw/` nunca se modifica en sitio.
- **FR-003**: Toda petición a la fuente MUST pedir unidades explícitas (temperatura °C, viento m/s, precipitación mm) y zona UTC, y la respuesta MUST verificarse contra esas unidades.
- **FR-004**: Cada etapa (raw → interim → processed) MUST validar sus datos contra un contrato versionado (columnas, tipos, unidades, rangos, unicidad de ubicación + hora, cobertura temporal) y detenerse si falla.
- **FR-005**: El pipeline MUST producir un reporte de calidad legible por máquina con el resultado de cada regla.
- **FR-006**: Todas las marcas de tiempo MUST almacenarse en UTC, con zona horaria explícita.
- **FR-007**: El dataset de modelado MUST contener, por ubicación y hora: identificador y coordenadas de la ubicación, hora UTC, las variables de pronóstico (temperatura, humedad relativa, punto de rocío, nubosidad, viento, dirección del viento, presión, precipitación pronosticada, energía convectiva disponible), la precipitación de referencia y la etiqueta binaria.
- **FR-008**: La etiqueta MUST ser `precipitación de referencia ≥ umbral`, con el umbral definido en un solo lugar y justificado con evidencia reproducible (calibración en la primera mitad del mes de SIATA, sin usar la segunda mitad).
- **FR-009**: Los CSV de SIATA MUST registrarse con su huella (checksum) y usarse solo para validación, nunca para entrenar.
- **FR-010**: La validación externa MUST producir el reporte descrito en US3: métricas en la mitad de validación, análisis de desfases, ciclo diurno y cuántas estaciones comparten celda de reanálisis.
- **FR-011**: La descarga MUST tolerar límites de tasa y errores temporales con reintentos y espera creciente, y respetar la política de uso gratuita de la fuente.
- **FR-012**: Repetir el comando con los mismos datos crudos MUST producir un dataset idéntico (determinista).

### Key Entities

- **Ubicación**: estación SIATA (código, nombre, municipio, latitud, longitud); identifica un punto del dataset.
- **Observación horaria**: ubicación + hora UTC + variables de pronóstico + precipitación de referencia + etiqueta.
- **Contrato de datos**: versión, columnas con tipo, unidad, rango y nulabilidad, claves únicas y cobertura esperada.
- **Reporte de calidad / de validación**: resultado de cada regla y métricas de concordancia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde un clon limpio, el dataset completo (13 ubicaciones × 35 064 horas) se reproduce con un comando en menos de 30 minutos con conexión normal.
- **SC-002**: Una segunda ejecución hace 0 descargas y produce un dataset con la misma huella.
- **SC-003**: El dataset final tiene 0 duplicados de ubicación + hora, ≥ 99 % de horas presentes por ubicación y 0 valores fuera de rango.
- **SC-004**: Cada una de las 5 alteraciones de prueba (rango, unidad, duplicado, hora faltante, columna faltante) detiene el pipeline con un mensaje que nombra la regla.
- **SC-005**: El reporte de validación externa cubre todas las estaciones con datos SIATA válidos suficientes (≥ 250 horas comparadas en la mitad de validación), lista las excluidas con su motivo y reporta métricas para la etiqueta y para el pronóstico crudo, por ventanas de 1 h, 3 h y 6 h. *(Ajustado en implementación: en los CSV disponibles la estación 205 no tiene minutos con calidad 1 y la 206 solo un 1.3 %, así que 11 de 13 estaciones son evaluables.)*

## Assumptions

- La fuente (Open-Meteo) sigue siendo gratuita y sin API key para uso no comercial, y su política de uso permite el volumen de este dataset.
- La precipitación de reanálisis tiene resolución espacial gruesa (~25 km); varias estaciones pueden compartir celda. Se documenta como limitación.
- Los CSV de SIATA solo cubren 2022-06-07 → 2022-07-07; la validación externa es de un mes y se presenta como tal.
- El script de entrenamiento antiguo (`mdva/modeling/train.py`) se reescribe en la spec 005; esta spec no entrena.
- Fuera de alcance: ingeniería de features (spec 004), modelos (spec 005), servir datos en vivo (spec 007).
