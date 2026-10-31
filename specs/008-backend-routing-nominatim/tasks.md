---

description: "Task list for 008-backend-routing-nominatim"
---

# Tasks: Backend — rutas con el routing service propio y geocodificación con Nominatim

**Tests**: pedidos por la spec (SC-004) y necesarios para probar sin red.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 [P] `services/routing_api/application/use_cases.py`: `/route/spring` devuelve la duración base (sin `× factor`), con test en `services/routing_api/tests/test_spring_duration.py` (grafo sintético)
- [X] T002 [P] `RoutingApiClient` + `RouteResult` + excepciones en `apps/backend/src/main/java/ti/mdva/service/routing/`, con `RoutingApiClientTest` (`MockRestServiceServer`: payload, mapeo de vehículo, pasos, alternativa distinta, 400 → sin ruta, conexión → no disponible)
- [X] T003 [P] `StopOrderOptimizer` en `apps/backend/src/main/java/ti/mdva/service/routing/` con `StopOrderOptimizerTest` (orden ingresado intacto, óptimo conocido, > 8 → error)

## Phase 2: User Story 1 + 2 - Planificar con rutas propias y paradas (Priority: P1/P2) 🎯 MVP

- [X] T004 [US1] [US2] `ViajeUseCase.planificarViaje` sin Google: coordenadas obligatorias, orden de paradas, una llamada de rutas, predicción de `WeatherMLService`, ajuste único en `TripPlannerOrchestrator`; tests en `apps/backend/src/test/java/ti/mdva/usecases/ViajeUseCasePlanificarTest.java`; ajustar `ViajeUseCaseAlertaActualTest`
- [X] T005 [US1] Eliminar `GoogleMapsService*`, `GoogleApiErrorTranslator*`, `EnvironmentalRoutingService*` y `google.*` de `application*.yml`; comentarios de DTOs sin Google

## Phase 3: User Story 3 - Geocodificación (Priority: P2)

- [X] T006 [US3] `NominatimClient` (caché 24 h, limitador 1 req/s, User-Agent, viewbox) en `apps/backend/src/main/java/ti/mdva/service/geocoding/` con `NominatimClientTest` (reloj y *sleeper* inyectables)
- [X] T007 [US3] `GeocodingController` (`/api/geocoding/search`, `/api/geocoding/reverse`) con `GeocodingControllerTest`; variables `NOMINATIM_URL`/`NOMINATIM_USER_AGENT` en `application.yml`, `.env.example` y compose

## Phase 4: User Story 4 - Errores explícitos (Priority: P3)

- [X] T008 [US4] `GlobalExceptionHandler`: `RoutingUnavailableException`/`GeocodingUnavailableException` → 503, `NoRouteException` → 422, mensajes sin detalles internos; tests en `GlobalExceptionHandlerTest`

## Phase 5: Polish

- [X] T009 `tests/e2e/smoke_stack.py`: planificar con coordenadas, geocodificación; stack reconstruido, smoke test, grep sin Google, tiempo de planificación; cerrar la spec (quickstart con verificación registrada)

## Dependencies & Execution Order

(T001, T002, T003) → T004 → T005 → (T006 → T007) → T008 → T009.
