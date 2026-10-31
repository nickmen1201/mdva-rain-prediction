# Quickstart: validar rutas propias y Nominatim

## 1. Tests

```bash
cd apps/backend && ./gradlew test          # contextLoads necesita PostgreSQL (como en CI)
make test                                  # pytest, incluye el routing service
```

Esperado: `RoutingApiClientTest`, `StopOrderOptimizerTest`, `NominatimClientTest`, `GeocodingControllerTest` y `ViajeUseCase*Test` en verde.

## 2. Stack y smoke test

```bash
make up
uv run python tests/e2e/smoke_stack.py
```

Esperado: `viajes_planificar` en 200 (antes 500), `geocoding_search` y `geocoding_reverse` en 200.

## 3. Cero referencias a Google Maps Platform

```bash
grep -rniE "google|googleapis" apps/backend/src/main/java apps/backend/src/main/resources/application*.yml   # sin resultados (las migraciones Flyway aplicadas no se editan)
```
