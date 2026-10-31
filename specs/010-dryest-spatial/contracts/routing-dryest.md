# Contract: ruta `dryest` espacial

## Dependencias consumidas (una vez por caja de viaje, caché 5 min)

| Servicio | Llamada |
|---|---|
| Open-Meteo Forecast | `GET /v1/forecast` con 25 pares `latitude`/`longitude` (malla 5 × 5) y los mismos parámetros que la señal puntual (spec 009) → arreglo de 25 ubicaciones |
| ML API v2 | `POST /v2/predict/batch` `{records: [25 × {time_utc, <variables del contrato>}]}` |

## Campos (aditivos)

| Campo | Dónde | Descripción |
|---|---|---|
| `rain_exposure` | cada opción de `/route`, `/route/spring` y sus `alternativas` | P(lluvia) media ponderada por tiempo a lo largo de la ruta; `null` sin grilla |
| `dryest_available` | `RouteResponse`, `SpringRouteResponse` | `true` si la grilla existe y su máximo ≥ 0.10 (se calculó `dryest`) |

`route_type = "dryest"` aparece solo si su camino difiere del de `fastest`.

## Backend

`RoutingApiClient` elige como alternativa la de `route_type = "dryest"` si existe; si no, la primera con geometría distinta (comportamiento de la spec 008). `TripResponseDTO.rutaAlternaTipo` informa el tipo. Clasificación: **aditivo**.
