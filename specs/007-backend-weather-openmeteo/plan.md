# Implementation Plan: Backend — clima con Open-Meteo y modelo v2

**Branch**: `007-backend-weather-openmeteo` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

## Summary

Dos clientes nuevos (`OpenMeteoForecastClient`, `MlApiV2Client`) reemplazan a Google Weather y a los endpoints v1 del ML API dentro de `WeatherMLServiceImpl` y `TripMonitorServiceImpl`. El snapshot guarda el instante real del dato. La tarjeta de predicción del Frontend deja de mostrar la regresión logística.

## Technical Context

**Language/Version**: Java 21, Spring Boot 3.4.2 (Backend); React 19 (un componente del Frontend)

**Primary Dependencies**: sin dependencias nuevas (RestTemplate, Jackson y spring-boot-starter-test ya presentes)

**Testing**: JUnit 5 + Mockito + `MockRestServiceServer`; smoke test del stack

**Constraints**: rutas y campos existentes intactos; sin API keys de clima; zonas horarias explícitas

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| II. Sin APIs de pago | Se retira Google Weather. | ✅ |
| IV. Contract-first | [contracts/backend-weather.md](contracts/backend-weather.md); cambio aditivo documentado. | ✅ |
| VI. Paridad train/serve | Misma fuente (Open-Meteo), mismas 9 variables y unidades, instante UTC; las features las calcula el ML API con `mdva`. | ✅ |
| VII. Sin datos fabricados | Fin de la mezcla con Google (H-21), del 0.0 del heatmap (H-22) y del "Reg. Logística 0 %". | ✅ |
| Timestamps UTC | Instantes UTC en el Backend; hora local solo para mostrar. | ✅ |

## Project Structure

```text
apps/backend/src/main/java/ti/mdva/
├── service/weather/OpenMeteoForecastClient.java   # nuevo
├── service/weather/HourlyInputs.java              # nuevo (registro de entrada del modelo)
├── service/weather/MlApiV2Client.java             # nuevo
├── service/impl/WeatherMLServiceImpl.java         # reescrito (sin Google)
├── service/impl/TripMonitorServiceImpl.java       # usa /v2/monitor/trip
├── model/dto/RainPredictionDTO.java               # + timestampDatoUtc
└── usecases/ViajeUseCase.java                     # snapshot con el instante del dato
apps/backend/src/test/java/ti/mdva/service/weather/{OpenMeteoForecastClientTest, MlApiV2ClientTest}.java
apps/backend/src/test/java/ti/mdva/service/impl/{WeatherMLServiceImplTest, TripMonitorServiceImplTest}.java
apps/frontend/src/components/AlertaClimatica.jsx
```

## Complexity Tracking

Sin violaciones.
