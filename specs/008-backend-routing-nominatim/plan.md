# Implementation Plan: Backend — rutas con el routing service propio y geocodificación con Nominatim

**Branch**: `008-backend-routing-nominatim` (trabajo directo en `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

## Summary

`GoogleMapsService` se elimina. Un `RoutingApiClient` llama una vez a `POST /api/v1/route/spring` (con las paradas ya ordenadas por `StopOrderOptimizer`) y devuelve la geometría y la duración base; la probabilidad de lluvia sale de `WeatherMLService` (spec 007) y la regla RF-10 la aplica solo `TripPlannerOrchestrator`. Un `NominatimClient` con caché de 24 h y limitador global de 1 consulta/s respalda los nuevos `GET /api/geocoding/search` y `GET /api/geocoding/reverse`. En el routing service, `/route/spring` deja de multiplicar la duración por el factor de alerta.

## Technical Context

**Language/Version**: Java 21, Spring Boot 3.4.2 (Backend); Python 3.11 (un cambio puntual en `services/routing_api`)

**Primary Dependencies**: sin dependencias nuevas. Caché y limitador con `ConcurrentHashMap` y un reloj inyectable (mismo patrón que `WeatherMLServiceImpl`); Caffeine/Bucket4j no se justifican para un solo cliente.

**Testing**: JUnit 5 + Mockito + `MockRestServiceServer`; pytest para el cambio del routing service; smoke test del stack (`tests/e2e/smoke_stack.py`).

**Constraints**: contratos de viajes intactos (FR-011); política de Nominatim (≤ 1 req/s, User-Agent, caché, sin autocompletado por tecla); sin API keys.

**Performance Goals**: planificar < 5 s con el grafo cargado (SC-005).

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| II. Sin APIs de pago | Se retira Google Directions/Geocoding; Nominatim y el routing service propio no requieren key. | ✅ |
| IV. Contract-first | [contracts/backend-routing-geocoding.md](contracts/backend-routing-geocoding.md): endpoints nuevos aditivos, consumo del routing service y cambio semántico de `/route/spring` (duración base) clasificado. | ✅ |
| VI. Paridad train/serve | La alerta usa la probabilidad del modelo evaluado con features de Open-Meteo (spec 007); se ignora el regresor del routing service. | ✅ |
| VII. Sin datos fabricados | Errores de rutas/geocodificación → Problem Details, nada se persiste; se elimina el *fallback* que mezclaba fuentes. | ✅ |
| Dependencias justificadas | Ninguna nueva. | ✅ |

## Project Structure

```text
apps/backend/src/main/java/ti/mdva/
├── service/routing/RoutingApiClient.java        # nuevo: /route/spring → RouteResult
├── service/routing/RouteResult.java             # nuevo (antes anidado en GoogleMapsService)
├── service/routing/StopOrderOptimizer.java      # nuevo: orden exhaustivo ≤ 8 paradas (haversine)
├── service/routing/RoutingUnavailableException.java, NoRouteException.java
├── service/geocoding/NominatimClient.java       # nuevo: búsqueda/reverso, caché 24 h, 1 req/s
├── service/geocoding/GeocodingResultDTO.java
├── controller/GeocodingController.java          # nuevo: /api/geocoding/{search,reverse}
├── usecases/ViajeUseCase.java                   # sin Google; una llamada de rutas
├── exception/GlobalExceptionHandler.java        # 503/422 para rutas y geocodificación
├── service/GoogleMapsService.java, impl/GoogleMapsServiceImpl.java,
│   GoogleApiErrorTranslator.java                # eliminados
└── service/EnvironmentalRoutingService.java, impl/EnvironmentalRoutingServiceImpl.java  # eliminados (reemplazados)
apps/backend/src/main/resources/application*.yml # sin google.*; + geocoding.nominatim.*
services/routing_api/application/use_cases.py    # /route/spring: duración base
tests/e2e/smoke_stack.py                         # planificar sin Google + geocodificación
```

## Complexity Tracking

Sin violaciones.
