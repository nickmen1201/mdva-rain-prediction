# Routing service — rutas sobre el grafo vial del Valle de Aburrá

Servicio FastAPI (DDD: `domain/`, `application/`, `infrastructure/`, `presentation/`) que calcula rutas sobre el grafo OSM de los 10 municipios del Valle de Aburrá con OSMnx + NetworkX. El único consumidor es el Backend (`/api/v1/route/spring`, spec 008).

## Qué hace

| Ruta | Costo de cada arista |
|---|---|
| `fastest` | tiempo de viaje (velocidad de la vía según OSM) × factor de alerta RF-10 |
| `shortest` | longitud |
| `dryest` | tiempo × factor × (1 + 3 · P(lluvia) en el punto medio de la arista), con P de una grilla 5 × 5 del modelo; solo si la grilla está disponible y su máximo es ≥ 0.10 |

- **Lluvia**: una sola señal, del modelo evaluado `rain_classifier` vía `POST /v2/predict` del ML API, con las variables de Open-Meteo de la hora UTC en curso (mismas variables y unidades del entrenamiento). Caché de 5 min por clave. Si Open-Meteo o el ML API fallan, la ruta se calcula sin factor y la respuesta trae `clima_disponible=false` (nunca valores inventados).
- **Bicicleta**: velocidad = mín(velocidad de la vía, 15 km/h).
- **Pasos**: aristas consecutivas de la misma vía agrupadas, con el nombre de OSM y giros a izquierda/derecha.
- **Sin elevaciones**: el factor de pendiente se retiró (sin DEM la pendiente era siempre 0); agregar un DEM y `rasterio` para un factor heurístico sin calibrar no se justificó (spec 010, research R4).

Historia: el regresor de intensidad heredado (con fuga del objetivo y elevaciones inventadas), el clima "promedio" de respaldo y el factor de tráfico constante se retiraron en la spec 009. Contratos: `specs/009-routing-cleanup/contracts/routing-api.md`, `specs/010-dryest-spatial/contracts/routing-dryest.md`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/route` | Opciones `fastest`, `shortest` y, si aplica, `dryest`, con `rain_exposure` |
| POST | `/api/v1/route/multi` | Ruta por paradas en orden |
| POST | `/api/v1/route/spring` | Formato del Backend: duración base (sin factor), pasos, alternativas |
| POST | `/api/v1/route/metrics` | Solo la señal de lluvia del origen |
| GET | `/health` | Healthcheck |

Documentación interactiva: http://localhost:8000/docs

## Configuración

| Variable | Default | Uso |
|---|---|---|
| `MDVA_ML_URL` | `http://ml-service:8081` | ML API v2 |
| `GRAPH_CACHE_FILE` | `valle_aburra.graphml` | Grafo en caché (volumen `routing_graph_cache` en Docker) |
| `CORS_ALLOWED_ORIGINS` | vacío | Orígenes permitidos, separados por comas (vacío: ninguno) |

El primer arranque descarga el grafo (2–10 min) y le agrega velocidades y tiempos por arista; un grafo cacheado antes de la spec 009 se completa una vez al cargarlo.

## Tests

```bash
uv run --project services/routing_api pytest services/routing_api/tests
```

Sin red ni grafo real: un grafo sintético de 5 nodos (avenida rápida vs. calle corta) y clientes HTTP simulados.
