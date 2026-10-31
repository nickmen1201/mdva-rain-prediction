# Contract: rutas y geocodificación en el Backend

## Dependencias externas (consumidas)

| Servicio | Llamada | Notas |
|---|---|---|
| Routing service | `POST /api/v1/route/spring` `{origen:{latitude,longitude}, destino:{…}, paradas:[…]?, vehicle_type: car\|motorcycle\|bike, route_type: "fastest"}` | Se leen `distanciaMetros`, `duracionSegundos` (**base, sin ajuste por lluvia** desde esta spec), `overviewPolyline`, `pasos[]`, `alternativas[]`. `400` = sin ruta. |
| Nominatim | `GET /search?q&format=jsonv2&limit=5&countrycodes=co&viewbox=-75.72,6.55,-75.30,6.00&bounded=1&accept-language=es` · `GET /reverse?lat&lon&format=jsonv2&accept-language=es` | User-Agent propio, ≤ 1 req/s global, caché 24 h. |

## Endpoints nuevos del Backend (aditivos, requieren `Authorization: Bearer`)

### `GET /api/geocoding/search?q={texto}`

- `q` con ≥ 3 caracteres no blancos; si no, `400` Problem Details.
- `200`: `[{ "displayName": "Parque Explora, Carrera 52, …", "lat": 6.2706, "lng": -75.5658, "tipo": "museum" }]` (0 a 5 elementos).
- `503` si Nominatim no responde.

### `GET /api/geocoding/reverse?lat={lat}&lng={lng}`

- `lat` ∈ [−90, 90], `lng` ∈ [−180, 180]; si no, `400`.
- `200`: `{ "displayName": "…", "lat": …, "lng": …, "tipo": "…" }`; `404` si Nominatim no encuentra dirección.

## Endpoints existentes (sin cambios de ruta ni de forma)

| Endpoint | Cambio |
|---|---|
| `POST /api/viajes/planificar` | Geometría del routing service; probabilidad del modelo v2. `origen`/`destino`/`paradas` MUST traer `lat`/`lng` (un `placeId` sin coordenadas → `400`). Nuevos errores: `503` (rutas no disponibles), `422` (sin ruta). Con `OPTIMIZAR_RUTA` y > 8 paradas → `400`. `paradasOrdenadas` refleja el orden calculado. |
| `GET /api/viajes/{id}`, historial, paradas | Sin cambios. |

Clasificación: **aditivo** para consumidores del Backend. `placeId` deja de resolverse (el Frontend actual ya envía coordenadas al elegir en el mapa; el autocompletado de Google se reemplaza en la spec 011).
