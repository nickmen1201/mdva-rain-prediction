# Feature Specification: Routing service — limpieza (una sola señal de lluvia, caché, sin datos inventados, tiempos reales)

**Feature Branch**: `009-routing-cleanup` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Spec 009 (charter R-25, R-28–R-33; H-10, H-11, H-12, H-15): eliminar el regresor de intensidad del routing service y sus derivados; la probabilidad de lluvia sale solo del ML API v2 con datos de Open-Meteo; caché con vencimiento por clave; sin valores de respaldo inventados (clima_disponible=false); tiempos de viaje desde velocidades por tipo de vía; zona horaria explícita; CORS configurable. Retirar los endpoints v1 del ML API y los modelos heredados (spec 007, Clarifications)."

## Clarifications

### Session 2026-10-31

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿De dónde saca el routing service la probabilidad de lluvia? → A: Pide a Open-Meteo las 9 variables del contrato de features para el origen y la hora UTC en curso (igual que el Backend, spec 007) y llama a `POST /v2/predict` del ML API. No calcula features: las calcula el ML API con `mdva` (P2).
- Q: ¿Cómo afecta la lluvia al costo de la ruta "fastest"? → A: El tiempo de cada arista se multiplica por el factor RF-10 del nivel de alerta (1.00/1.20/1.35). Con un factor uniforme el camino óptimo no cambia —se documenta—; la variación espacial real llega con `dryest` en la spec 010.
- Q: ¿Qué velocidad se usa para bicicleta? → A: El mínimo entre la velocidad de la vía y 15 km/h (velocidad urbana típica de bicicleta), documentado como supuesto. Para moto y carro, la velocidad de la vía (`maxspeed` de OSM o la imputada por tipo de vía).
- Q: ¿Se conserva la penalización por pendiente para bicicleta? → A: No en esta spec: sin elevaciones el factor es siempre 1 (R-27). La spec 010 decide si se agregan elevaciones reales.
- Q: ¿Se conserva el factor de "tráfico" ×1.5 en vías principales? → A: No: es una constante sin fuente que distorsiona el costo; el tiempo por tipo de vía ya refleja la jerarquía vial. Se documenta como cambio de comportamiento.
- Q: ¿Qué campos de la respuesta cambian? → A: Se eliminan los derivados del regresor (`rain_intensity_avg`, `elevation_avg`, `rain_factor` heredado, `mdva_probabilidad_rl`, variables meteorológicas copiadas); se agregan `rain_probability` ∈ [0, 1] del modelo, `alerta_nivel`, `clima_disponible` y `model_version`. El único consumidor (el Backend, desde la spec 008) solo lee geometría, duración y pasos.
- Q: ¿Se retiran los endpoints v1 del ML API (`/predecir/*`, `/monitorear/trayecto`)? → A: Sí: tras esta spec ningún servicio los usa. Requiere enmendar el charter (RF-22/RF-23 describen modelos que ya no existen) y elimina los `.pkl` heredados (67 MB en git, P7).

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien revisa** el portafolio (el sistema usa un solo modelo evaluado, sin datos inventados) y **la persona que planifica** (tiempos de viaje más realistas).

### User Story 1 - Una sola señal de lluvia, del modelo evaluado (Priority: P1)

Las rutas del routing service usan la probabilidad del modelo evaluado en la spec 005; el modelo de intensidad heredado, con fuga de datos y features inventadas, desaparece.

**Why this priority**: H-10 y H-11 son defectos de ML que contradicen la evaluación honesta del resto del proyecto.

**Independent Test**: pedir una ruta con el ML API simulado devolviendo 0.75 y verificar `rain_probability = 0.75`, `alerta_nivel = ROJO` y tiempos × 1.35.

**Acceptance Scenarios**:

1. **Given** el ML API responde 0.75, **When** se pide una ruta, **Then** la respuesta trae `rain_probability = 0.75`, `alerta_nivel = ROJO`, `clima_disponible = true` y la versión del modelo.
2. **Given** el repositorio tras la spec, **When** se busca el regresor de intensidad y sus artefactos, **Then** no existen.

---

### User Story 2 - Sin datos inventados cuando falla el clima (Priority: P1)

Si Open-Meteo o el ML API fallan, la ruta se calcula igual, sin penalización por lluvia, y la respuesta lo declara.

**Why this priority**: hoy se inventa "clima promedio de Medellín" y se predice sobre él sin avisar (H-11, constitución VII).

**Independent Test**: simular la caída de Open-Meteo y del ML API por separado.

**Acceptance Scenarios**:

1. **Given** Open-Meteo caído, **When** se pide una ruta, **Then** responde 200 con `clima_disponible = false`, `rain_probability = null` y tiempos sin factor.
2. **Given** el ML API rechaza o no responde, **When** se pide una ruta, **Then** igual que el anterior.

---

### User Story 3 - Caché correcta (Priority: P2)

Cada consulta de clima se reutiliza durante 5 minutos y vence por su cuenta.

**Why this priority**: hoy una única marca de tiempo global sirve entradas viejas como frescas (H-12).

**Independent Test**: dos puntos consultados en momentos distintos; avanzar el reloj y verificar que solo vence el más antiguo.

**Acceptance Scenarios**:

1. **Given** el punto A consultado en t=0 y B en t=4 min, **When** se consulta A y B en t=6 min, **Then** A se vuelve a pedir y B sale de caché.

---

### User Story 4 - Tiempos de viaje realistas (Priority: P2)

La duración de la ruta y de cada paso refleja la velocidad de cada tipo de vía en lugar de 40 km/h fijos.

**Independent Test**: en un grafo sintético con una autopista y una calle residencial, la ruta más rápida prefiere la autopista aunque sea más larga, y la duración coincide con la suma de los tiempos de las aristas.

**Acceptance Scenarios**:

1. **Given** dos caminos, uno más corto por vía residencial y otro más largo por vía arterial más rápida, **When** se pide `fastest`, **Then** se elige el de menor tiempo y `shortest` el de menor distancia.
2. **Given** una ruta en bicicleta, **When** se calcula, **Then** ninguna arista supera 15 km/h.
3. **Given** una ruta, **When** se generan los pasos, **Then** agrupan aristas consecutivas de la misma vía, nombran la vía cuando OSM la tiene, y sus duraciones suman la duración total.

---

### User Story 5 - Configuración segura y servicios sin código muerto (Priority: P3)

CORS limitado a orígenes configurados, sin parámetros sin uso, hora con zona explícita, logging en lugar de `print`, y el ML API sin endpoints ni modelos heredados.

**Acceptance Scenarios**:

1. **Given** `CORS_ALLOWED_ORIGINS` configurado, **When** llega una petición de otro origen, **Then** no recibe cabeceras CORS.
2. **Given** el ML API tras la spec, **When** se llama a `/predecir/random_forest`, **Then** responde 404; `/health` y `/v2/*` siguen funcionando.

### Edge Cases

- Ruta con origen y destino en el mismo nodo: distancia 0, una ruta, sin pasos (comportamiento actual).
- Arista sin `maxspeed` ni tipo conocido: velocidad imputada por OSMnx (media de su tipo o de todo el grafo).
- `CORS_ALLOWED_ORIGINS` vacío: no se permite ningún origen cruzado (el Backend llama servidor a servidor).
- El grafo en caché fue creado antes de esta spec (sin `travel_time`): se calculan velocidades y tiempos al cargarlo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El routing service MUST NOT contener ni cargar el regresor de intensidad, su script de entrenamiento ni su artefacto (D-02, D-03, D-04).
- **FR-002**: La probabilidad de lluvia MUST obtenerse del ML API v2 con las variables de Open-Meteo de la hora UTC en curso, pedidas con unidades explícitas y verificadas.
- **FR-003**: Las consultas de clima/predicción MUST cachearse 5 min con vencimiento por clave (coordenadas redondeadas a 2 decimales).
- **FR-004**: Si el clima o la predicción fallan, la ruta MUST calcularse sin factor de lluvia y declarar `clima_disponible = false`; MUST NOT usarse ningún valor por defecto.
- **FR-005**: Los tiempos MUST salir de velocidades por arista (OSM) y la lluvia MUST aplicarse como factor RF-10 sobre esos tiempos; bicicleta limitada a 15 km/h.
- **FR-006**: `fastest` MUST minimizar tiempo y `shortest` distancia; la respuesta MUST incluir la duración total como suma de tiempos de arista.
- **FR-007**: Los pasos de navegación MUST agrupar aristas de la misma vía, incluir su nombre cuando exista y sumar la duración total.
- **FR-008**: CORS MUST limitarse a `CORS_ALLOWED_ORIGINS` (lista separada por comas).
- **FR-009**: La hora MUST tomarse en UTC tz-aware; MUST NOT quedar parámetros sin uso (`api_key`, `base_url` de OpenWeatherMap); los mensajes MUST ir por `logging`.
- **FR-010**: El ML API MUST retirar `/predecir/*` y `/monitorear/trayecto` (v1) y los `.pkl` heredados; `/health` y `/v2/*` MUST seguir igual.
- **FR-011**: Los endpoints del routing service (RF-15) MUST conservar rutas y campos de geometría; los cambios de campos de lluvia se documentan en el contrato.

### Key Entities

- **Señal de lluvia**: probabilidad ∈ [0, 1] o ausente, nivel de alerta, versión del modelo, instante UTC del dato, disponible sí/no.
- **Arista ponderada**: longitud, velocidad, tiempo de viaje, nombre de vía.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 archivos del regresor de intensidad y 0 modelos heredados versionados; el repositorio pierde los 67 MB de `random_forest.pkl` y el `rain_model.joblib`.
- **SC-002**: Los tests del routing service corren sin red ni grafo OSM real (grafo sintético) y cubren: señal de lluvia, caída de clima/ML, caché por clave, tiempos por vía, bicicleta, pasos.
- **SC-003**: El smoke test de punta a punta sigue en verde (planificar 200) y la duración de una ruta urbana de ~5 km queda entre 6 y 20 min (antes: siempre distancia / 40 km/h).
- **SC-004**: `scikit-learn` deja de ser dependencia del routing service (era 1.9.1 con un modelo serializado en 1.8.0).

## Assumptions

- Velocidades: las de OSMnx (`add_edge_speeds`) a partir de `maxspeed` y tipo de vía; no hay tráfico en vivo.
- Fuera de alcance: penalización espacial por arista (`dryest`) y elevaciones (spec 010).
