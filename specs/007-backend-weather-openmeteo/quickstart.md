# Quickstart: validar el clima del Backend

## 1. Tests

```bash
cd apps/backend && ./gradlew test   # contextLoads necesita PostgreSQL (como en CI)
```

Esperado: clientes de Open-Meteo y del ML API v2, `WeatherMLServiceImpl`, monitoreo y controlador en verde.

## 2. Stack y smoke test

```bash
make up
uv run python tests/e2e/smoke_stack.py
```

Esperado: `weather_current`, `weather_forecast` y `weather_predict_grid_81` en 200; el resto igual a la línea base de la spec 006.

## 3. Cero referencias a Google Weather

```bash
grep -rni "google" apps/backend/src/main | grep -i weather   # sin resultados
```

## Verificación registrada (2026-10-29)

- **SC-001** ✅ clima actual 200 (antes 502) y pronóstico 200. Respuesta con `timestampDatoUtc` = hora UTC en curso (14:00Z a las 14:23Z) y sin `probabilidadRl`.
- **SC-002** ✅ heatmap de 81 puntos: 1 llamada a Open-Meteo (verificada en `WeatherMLServiceImplTest`), **1** a `/v2/predict/batch` (contada en los logs del ML API) y 1.2 s de respuesta.
- **SC-003** ✅ 0 referencias a Google Weather en `apps/backend/src/main`.
- **SC-004** ✅ 171 tests del Backend en verde (con PostgreSQL efímero para `contextLoads`).
- **SC-005** ✅ resto del smoke test idéntico a la línea base; `viajes_planificar` sigue en 500 por Google Directions (spec 008).
- FR-009: el pronóstico devuelve `14:00Z → hora 9` (Bogotá, UTC−5) dentro del contenedor.
- Hallazgos al levantar el stack, corregidos: (1) `WeatherMLServiceImpl` tenía dos constructores sin `@Autowired` y el contexto no arrancaba; (2) el cliente HTTP por defecto de `RestTemplateBuilder` (JDK) intenta `Upgrade: h2c` y uvicorn descarta el cuerpo del POST (422 "Field required"); `MlApiV2Client` usa HTTP/1.1 explícito.
