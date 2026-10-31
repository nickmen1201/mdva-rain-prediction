# Implementation Plan: Routing service — limpieza

**Branch**: `009-routing-cleanup` (trabajo directo en `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

## Summary

Se elimina el regresor de intensidad (D-02, D-03, D-04) y el `WeatherService` heredado. Un `RainSignalClient` (Open-Meteo + `POST /v2/predict`, caché TTL por clave, sin valores por defecto) da la única señal de lluvia. El grafo gana `speed_kph`/`travel_time` de OSMnx; el costo `fastest` es tiempo × factor RF-10 y `shortest` es longitud; bicicleta a ≤ 15 km/h. Los pasos se agrupan por vía con su nombre. Un índice propio de nodo más cercano permite quitar `scikit-learn`. En el ML API se retiran los endpoints y modelos v1, con enmienda del charter.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: OSMnx 2.1.1, NetworkX 3.6.1, FastAPI, `requests` (ya presentes). Se **quitan** `scikit-learn`, `joblib` y `pandas` del routing service si nada más los usa. Sin dependencias nuevas.

**Testing**: pytest con grafo sintético (`networkx.MultiDiGraph` de 6–10 nodos con `x`, `y`, `length`, `highway`, `name`, `maxspeed`) y clientes HTTP simulados (`requests` con un *session* inyectable); `TestClient` para CORS y endpoints.

**Constraints**: rutas de RF-15 intactas; tests sin red ni grafo real (R-40).

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| IV. Contract-first | [contracts/routing-api.md](contracts/routing-api.md): campos eliminados/agregados clasificados (rompientes solo para campos sin consumidores). | ✅ |
| VI. Paridad train/serve | Misma fuente, 9 variables, unidades explícitas e instante UTC que el entrenamiento; features en el ML API. | ✅ |
| VII. Sin datos fabricados | Fin del clima "promedio", la elevación 1500, `probability = intensity × 25` y `traffic_factor`; `clima_disponible=false`. | ✅ |
| II/P7. Reproducible, artefactos fuera de git | Se borran `rain_model.joblib` (4.6 MB) y los `.pkl` v1 (67 MB). | ✅ |
| Dependencias justificadas | Se quitan tres; ninguna nueva (caché e índice con stdlib/numpy). | ✅ |

## Project Structure

```text
services/routing_api/
├── domain/entities.py                    # Route sin campos del regresor; RainSignal
├── domain/rain_model.py                  # eliminado (D-03)
├── train_rain_model.py, cache/rain_model.joblib   # eliminados (D-02, D-03)
├── infrastructure/weather_service.py     # eliminado → rain_signal.py
├── infrastructure/rain_signal.py         # nuevo: Open-Meteo + /v2/predict + TTLCache
├── infrastructure/nearest.py             # nuevo: NearestNodeIndex (numpy)
├── infrastructure/osmnx_map_repository.py # speeds/travel_time al cargar; logging
├── infrastructure/networkx_routing_service.py # costos por tiempo/longitud, bici 15 km/h
├── application/navigation.py             # nuevo: pasos agrupados por vía
├── application/dtos.py, use_cases.py     # campos nuevos, sin promedios inventados
├── main.py                               # CORS por env, logging
├── pyproject.toml, uv.lock               # sin scikit-learn/joblib/pandas
└── tests/                                # grafo sintético
services/ml_api/main.py                   # sin v1
models/random_forest.pkl, models/regresion_logistica.pkl   # eliminados
.specify/memory/charter.md                # 2.0.0: RF-17, RF-22, RF-23
```

## Complexity Tracking

Sin violaciones.
