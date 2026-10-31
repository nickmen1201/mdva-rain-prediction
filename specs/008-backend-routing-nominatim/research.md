# Research: Backend — rutas propias y Nominatim

## R1. Hallazgos al leer el código actual

| ID | Hallazgo | Evidencia |
|---|---|---|
| H-25 | La planificación usa Google Directions para la geometría y el routing service solo para "métricas"; si las métricas fallan cae a otra fuente de predicción (`fallback a ML clásico`): dos caminos de predicción distintos según la disponibilidad | `ViajeUseCase.planificarViaje` |
| H-26 | El tiempo base se multiplica por `rain_factor` del regresor del routing service y **luego** por el factor RF-10: doble ajuste por lluvia | `ViajeUseCase` paso 4 + `TripPlannerOrchestrator.apply` |
| H-27 | `/route/spring` ya devuelve la duración multiplicada por el factor de alerta calculado con el RF v1 | `use_cases.py::execute_spring` (`adjusted_duration`) |
| H-28 | El Backend envía `vehicle_type` `moto`/`bicycle`, que el routing service no reconoce (`car`, `motorcycle`, `bike`) | `ViajeUseCase` vs `networkx_routing_service.py` |
| H-29 | `/route/metrics` llama al ML v1 desde el routing service: tercera ruta de predicción | `presentation/api.py` |

## R2. Una sola llamada de rutas

- **Decision**: `RoutingApiClient.route(origen, destino, paradasOrdenadas, vehicleType)` → `POST /api/v1/route/spring` con `route_type=fastest`. Se leen `distanciaMetros`, `duracionSegundos`, `overviewPolyline`, `pasos` y la primera entrada de `alternativas` con polyline distinta (FR-006). Los campos de lluvia de la respuesta no se leen.
- **Rationale**: `/route/spring` ya resuelve multi-parada; una llamada evita recalcular el grafo dos veces (SC-005).
- **Errores**: conexión rechazada / timeout → `RoutingUnavailableException` (503); `400` del routing service (sin ruta: `RouteNotFoundError`) → `NoRouteException` (422).
- **HTTP/1.1 explícito** (`SimpleClientHttpRequestFactory`): mismo problema `Upgrade: h2c` con uvicorn documentado en la spec 007. Timeout de lectura 60 s (la primera ruta tras arrancar carga el grafo).

## R3. Orden óptimo de paradas

- **Decision**: con `OPTIMIZAR_RUTA`, permutaciones de las paradas (origen y destino fijos) minimizando la suma de distancias haversine; ≤ 8 paradas (8! = 40 320 permutaciones, < 50 ms). Más de 8 → 400.
- **Alternatives considered**: matriz de distancias de red con el routing service (N² rutas, segundos por viaje); vecino más cercano (no óptimo). La línea recta es un proxy razonable en un valle urbano y se documenta.

## R4. Nominatim

- **Decision**: `GET {base}/search?q=..&format=jsonv2&limit=5&countrycodes=co&viewbox=-75.72,6.55,-75.30,6.00&bounded=1&accept-language=es` y `GET {base}/reverse?lat=..&lon=..&format=jsonv2&accept-language=es`.
- **Política** (https://operations.osmfoundation.org/policies/nominatim/): User-Agent identificable (`geocoding.nominatim.user-agent`, por defecto `MDVA/1.0 (+https://github.com/nickmen1201/mdva-rain-prediction)`), máximo 1 petición/s, caché de resultados, sin autocompletado en vivo. Un limitador global (`synchronized` + último instante) espera hasta completar 1 s desde la consulta anterior.
- **Caché**: clave = texto normalizado (minúsculas, espacios colapsados, sin tildes) o coordenadas redondeadas a 5 decimales; TTL 24 h; máximo 1 000 entradas (se purgan las vencidas al insertar).
- **URL base configurable** (`NOMINATIM_URL`) para poder apuntar a una instancia propia.

## R5. Duración base en `/route/spring`

- **Decision**: `execute_spring` devuelve `int(best.travel_time_seconds)` y las alternativas sin `× factor`. Los campos de alerta del routing service se conservan (los usa `/route` de forma directa) hasta la spec 009.
- **Clasificación**: cambio semántico en un campo de un endpoint interno cuyo único consumidor es el Backend; se documenta en el contrato.
