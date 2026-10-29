---

description: "Task list for 007-backend-weather-openmeteo"
---

# Tasks: Backend — clima con Open-Meteo y modelo v2

**Tests**: pedidos por la spec (SC-004) y necesarios para probar sin red.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 [P] `HourlyInputs` y `OpenMeteoForecastClient` en `apps/backend/src/main/java/ti/mdva/service/weather/` con tests (`MockRestServiceServer`: URL, unidades, una y varias ubicaciones, hora en curso)
- [X] T002 [P] `MlApiV2Client` en `apps/backend/src/main/java/ti/mdva/service/weather/` con tests (lote, monitoreo, 422 → error explícito)

## Phase 2: User Story 1 + 2 - Clima actual, pronóstico y heatmap (Priority: P1) 🎯 MVP

- [X] T003 [US1] [US2] Reescribir `WeatherMLServiceImpl` sin Google Weather (actual, horario, grilla) y `RainPredictionDTO.timestampDatoUtc`; tests en `WeatherMLServiceImplTest`; ajustar `WeatherControllerTest`

## Phase 3: User Story 3 - Monitoreo (Priority: P2)

- [X] T004 [US3] `TripMonitorServiceImpl` con `/v2/monitor/trip` y snapshot con el instante del dato en `ViajeUseCase`; actualizar `TripMonitorServiceImplTest`

## Phase 4: User Story 4 - Interfaz (Priority: P3)

- [X] T005 [US4] `apps/frontend/src/components/AlertaClimatica.jsx`: una sola probabilidad rotulada "Probabilidad de lluvia"

## Phase 5: Polish

- [X] T006 Stack reconstruido, smoke test (clima actual 200), conteo de llamadas del heatmap, 0 referencias a Google Weather; cerrar la spec

## Dependencies & Execution Order

(T001, T002) → T003 → T004 → T005 → T006.
