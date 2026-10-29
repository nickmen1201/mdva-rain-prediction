# Research: Backend — clima con Open-Meteo y modelo v2

## R1. Hallazgos al leer el código actual

| ID | Hallazgo | Evidencia |
|---|---|---|
| H-21 | La probabilidad mostrada es `0.65·RF + 0.35·prob_Google`, sin evaluación ni documentación | `WeatherMLServiceImpl.predictRainForLocation` |
| H-22 | Si falla un punto del heatmap se devuelve probabilidad 0.0 (dato fabricado) | `WeatherMLServiceImpl.predictGridPoint` |
| H-23 | El snapshot del viaje guarda `OffsetDateTime.now()` como instante del dato meteorológico | `ViajeUseCase` (paso 5.1) |
| H-24 | El pronóstico horario interpreta horas de Open-Meteo (`timezone=auto`) con la zona del servidor; en contenedor (UTC) las horas quedan corridas | `getHourlyForecast` |
| — | RF-11 ("precipitación > 0.1 mm fuerza llueve") no existe en el código | búsqueda en `apps/backend` |

## R2. Una sola consulta de clima

- **Decision**: `OpenMeteoForecastClient` pide `hourly=<9 variables>`, `forecast_days=2`, `timezone=GMT`, `wind_speed_unit=ms`, `temperature_unit=celsius`, `precipitation_unit=mm`, con coordenadas separadas por comas para varias ubicaciones (heatmap) y verifica `hourly_units` como en la spec 003.
- **Rationale**: la misma petición sirve para la hora en curso (clima actual y monitoreo) y para las siguientes (pronóstico); varias ubicaciones van en una sola llamada (SC-002).

## R3. Cliente del ML API v2

- **Decision**: `MlApiV2Client` con `predictBatch(List<HourlyInputs>)` → `/v2/predict/batch` y `monitorTrip(...)` → `/v2/monitor/trip`. Los 422 se propagan como `IllegalStateException` con el detalle del Problem Details; no hay valores por defecto.

## R4. Cachés

- **Decision**: se conservan los TTL actuales (predicción puntual 180 s, heatmap 180 s), con claves redondeadas como hoy; además, la consulta de clima por punto se cachea 180 s para que el monitoreo no la repita.

## R5. Pruebas sin red

- **Decision**: clientes con `RestTemplate` inyectable y `MockRestServiceServer` (spring-boot-starter-test); el servicio se prueba con los clientes simulados con Mockito.
