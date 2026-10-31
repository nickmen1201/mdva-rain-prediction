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

## Verificación registrada (2026-10-31)

- **SC-001** ✅ `POST /api/viajes/planificar` → 201 (antes 500) con polyline, alerta VERDE y `GET /api/viajes/{id}` 200, sin ninguna API key en el `.env`.
- **SC-002** ✅ 0 coincidencias de `google|googleapis` en `apps/backend/src/main/java` y `application*.yml`.
- **SC-003** ✅ caché y limitador probados con reloj manual en `NominatimClientTest` (búsqueda repetida y normalizada → 1 consulta; 3 búsquedas distintas → esperas de 0.7 s y 1 s). En el stack, `geocoding_search` ("Parque Explora") y `geocoding_reverse` → 200 con resultados.
- **SC-004** ✅ 194 tests del Backend en verde (PostgreSQL efímero para `contextLoads`); 18 tests del routing service.
- **SC-005** ✅ planificar Parque Berrío → El Poblado respondió en < 5 s con el grafo cargado (smoke test completo: 10.3 s, 20 comprobaciones).
