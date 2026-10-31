# Feature Specification: Backend — rutas con el routing service propio y geocodificación con Nominatim

**Feature Branch**: `008-backend-routing-nominatim` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Spec 008 (charter R-35b, H-19): el Backend deja de usar Google Directions y Google Geocoding. Las rutas de POST /api/viajes/planificar (y multi-parada) se obtienen del routing service propio (/api/v1/route/spring y /route/multi), y la geocodificación de direcciones/autocompletado se hace con Nominatim (OSM) respetando su política (User-Agent identificable, ≤ 1 req/s, caché). Restablecer RF-09 de punta a punta sin ninguna API key."

## Clarifications

### Session 2026-10-31

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿El autocompletado consulta a Nominatim en cada tecla? → A: No. La política de uso de Nominatim prohíbe el autocompletado contra su servidor público. La búsqueda se dispara al enviar el texto (Enter o botón); el Backend agrega caché de 24 h y ≤ 1 consulta/s. El Frontend lo adopta en la spec 011.
- Q: ¿Qué probabilidad de lluvia decide la alerta? → A: La del modelo `rain_classifier` vía el flujo de clima del Backend (spec 007), en el origen. Los campos de lluvia que hoy devuelve el routing service (regresor interno, H-10) se ignoran; se eliminan en la spec 009.
- Q: El routing service ya multiplica la duración por el factor de alerta; ¿se conserva? → A: No: daría un doble ajuste. `/route/spring` devuelve la duración base y el Backend es el único dueño de la regla RF-10.
- Q: ¿Se conserva el ajuste de −15 % para motos? → A: Sí: es una regla existente del equipo sobre el tiempo base; se mantiene sin cambios.
- Q: ¿Y "evitar el Túnel de Oriente" para motos (peajes)? → A: Se retira: el grafo cubre solo los 10 municipios del valle (RF-04) y el túnel conecta con Rionegro, fuera del grafo; ninguna ruta posible lo cruza.
- Q: ¿Cuántas llamadas al routing service por viaje? → A: Una: `/route/spring` con las paradas ya ordenadas; la alternativa sale del campo `alternativas` de la misma respuesta.
- Q: ¿Qué pasa con `placeId` (Google Places) en la petición? → A: Se conserva en el contrato por compatibilidad, pero si un punto llega sin coordenadas la petición se rechaza con 400.

## User Scenarios & Testing *(mandatory)*

Usuarios: **la persona que planifica viajes** y **quien revisa** el portafolio (el producto corre sin servicios de pago y el modelo evaluado es el que decide la alerta).

### User Story 1 - Planificar un viaje sin servicios de pago (Priority: P1)

La persona elige origen y destino (por coordenadas) y recibe la ruta, la alerta de lluvia y el tiempo ajustado; el viaje queda guardado en su historial.

**Why this priority**: es la función central del producto (charter RF-09) y hoy responde 500 porque Google Directions no tiene facturación (H-19).

**Independent Test**: con el stack arriba y sin ninguna API key, planificar un viaje entre dos puntos de Medellín y consultarlo después por su id.

**Acceptance Scenarios**:

1. **Given** el stack sin API keys, **When** se planifica un viaje entre dos puntos del valle, **Then** responde 200 con polyline no vacía, distancia > 0, tiempo base, nivel de alerta, factor y tiempo ajustado según RF-10, y el viaje aparece en el historial.
2. **Given** una probabilidad de lluvia conocida del modelo, **When** se planifica, **Then** el nivel y el factor siguen la tabla RF-10 y el tiempo ajustado = tiempo base × factor (el ajuste por lluvia se aplica una sola vez).
3. **Given** un viaje en moto o en bicicleta, **When** se planifica, **Then** el servicio de rutas recibe el tipo de vehículo correspondiente.

---

### User Story 2 - Viajes con paradas (Priority: P2)

La persona agrega paradas intermedias en el orden que quiere, o pide que se optimice el orden.

**Why this priority**: funcionalidad existente (RF-12) que dependía del reordenamiento de Google.

**Independent Test**: planificar con 2 paradas en ambos modos y verificar el orden devuelto y la persistencia de las paradas.

**Acceptance Scenarios**:

1. **Given** paradas en modo "orden ingresado", **When** se planifica, **Then** la ruta pasa por ellas en ese orden y se guardan con ese orden.
2. **Given** paradas en modo "optimizar", **When** se planifica, **Then** se devuelve el orden que minimiza la distancia en línea recta del recorrido completo (origen y destino fijos), y la ruta sigue ese orden.

---

### User Story 3 - Buscar direcciones por texto (Priority: P2)

La persona escribe una dirección o lugar del valle y obtiene una lista de coincidencias con nombre y coordenadas; también puede obtener el nombre de un punto tocado en el mapa.

**Why this priority**: reemplaza Google Places/Geocoding; lo consume el Frontend en la spec 011.

**Independent Test**: buscar "Parque Explora" y obtener al menos un resultado dentro del Valle de Aburrá; repetir la búsqueda y verificar que no se repite la consulta externa.

**Acceptance Scenarios**:

1. **Given** un texto de búsqueda, **When** se busca, **Then** se devuelven hasta 5 resultados con nombre legible, latitud y longitud, limitados al Valle de Aburrá.
2. **Given** la misma búsqueda dentro de 24 h, **When** se repite, **Then** se responde desde caché.
3. **Given** ráfagas de búsquedas, **When** llegan, **Then** el Backend nunca envía más de 1 consulta por segundo al proveedor y se identifica con un User-Agent propio.
4. **Given** un par de coordenadas, **When** se pide su nombre, **Then** se devuelve una dirección legible.

---

### User Story 4 - Errores explícitos (Priority: P3)

Si el servicio de rutas o el de geocodificación no responden, o no existe ruta entre los puntos, la persona recibe un mensaje claro y no se guarda un viaje inventado.

**Independent Test**: apagar el routing service y planificar; pedir una ruta con un punto fuera del grafo.

**Acceptance Scenarios**:

1. **Given** el servicio de rutas caído, **When** se planifica, **Then** responde 503 con mensaje genérico y no se persiste ningún viaje.
2. **Given** puntos sin ruta posible, **When** se planifica, **Then** responde 422 con un mensaje claro.
3. **Given** una petición con identificador de Google Places y sin coordenadas, **When** se planifica, **Then** responde 400 indicando que se envíen coordenadas.

### Edge Cases

- Origen y destino iguales: 400 (comportamiento actual).
- Búsqueda de texto vacía o de menos de 3 caracteres: 400, sin llamar al proveedor.
- El proveedor de geocodificación devuelve 0 resultados: lista vacía (200).
- La predicción de lluvia falla: el viaje no se planifica con una probabilidad inventada; error explícito (constitución VII).
- Más de 8 paradas en modo "optimizar": 400 (el orden óptimo exacto deja de ser barato de calcular).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La planificación MUST obtener distancia, duración, polyline y pasos únicamente del routing service propio; MUST NOT llamar a Google.
- **FR-002**: La probabilidad de lluvia de la alerta MUST venir del modelo evaluado (specs 005/006) a través del flujo de clima de la spec 007, no de valores calculados por el routing service.
- **FR-003**: El ajuste de tiempo por lluvia (RF-10) MUST aplicarse exactamente una vez, en el Backend, sobre la duración base devuelta por el routing service.
- **FR-004**: El tipo de vehículo MUST mapearse a los valores que acepta el routing service (carro → `car`, moto → `motorcycle`, bicicleta → `bike`).
- **FR-005**: El modo "optimizar paradas" MUST devolver el orden de mínima distancia en línea recta (búsqueda exhaustiva, ≤ 8 paradas); el modo "orden ingresado" MUST respetar el orden recibido.
- **FR-006**: La ruta alternativa (cuando el routing service la ofrece con geometría distinta) MUST seguir disponible para el usuario (RF-14).
- **FR-007**: El Backend MUST exponer búsqueda de direcciones por texto y nombre por coordenadas, autenticadas como el resto de `/api/**`.
- **FR-008**: Las consultas al proveedor de geocodificación MUST ir con un User-Agent identificable y configurable, a ≤ 1 consulta/s global, con caché de 24 h por consulta normalizada, y limitadas al Valle de Aburrá (Colombia).
- **FR-009**: Ningún error del routing service ni del geocodificador MUST convertirse en datos inventados; se responde con Problem Details y sin persistir.
- **FR-010**: El código y la configuración del Backend MUST quedar sin referencias a Google Maps Platform.
- **FR-011**: Los contratos externos existentes (`TripRequestDTO`, `TripResponseDTO`, endpoints de viajes) MUST mantenerse; solo se agregan campos o endpoints.

### Key Entities

- **Punto de viaje**: nombre legible + coordenadas (el identificador de Google queda obsoleto).
- **Resultado de geocodificación**: nombre legible, latitud, longitud, tipo de lugar.
- **Ruta calculada**: distancia, duración base, polyline, pasos, ruta alternativa opcional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El smoke test de punta a punta planifica un viaje con respuesta 200 (antes 500) sin ninguna API key configurada.
- **SC-002**: 0 referencias a Google Maps Platform en código y configuración del Backend (las migraciones Flyway ya aplicadas y el código JOOQ generado quedan como historia).
- **SC-003**: Una búsqueda repetida no genera una segunda consulta externa; búsquedas distintas en ráfaga salen espaciadas ≥ 1 s.
- **SC-004**: Los tests del Backend pasan, incluidos los nuevos de cliente de rutas, geocodificación y orden de paradas.
- **SC-005**: Planificar un viaje urbano típico (< 15 km) responde en menos de 5 s con el grafo ya cargado.

## Assumptions

- El routing service ya cubre el Valle de Aburrá (RF-04) y su endpoint `/route/spring` es el sustituto diseñado de Directions.
- El tiempo del routing service no incluye tráfico en vivo; se acepta (no hay fuente gratuita de tráfico). Los tiempos por tipo de vía llegan en la spec 009.
- Fuera de alcance: limpiar el modelo de lluvia interno del routing service (spec 009), ruta `dryest` real (spec 010), cambios en el Frontend (spec 011).
