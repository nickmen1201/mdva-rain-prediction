# Implementation Plan: Ruta `dryest` espacial real

**Branch**: `010-dryest-spatial` (trabajo directo en `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

## Summary

`RainGridClient` (en `infrastructure/rain_signal.py`) pide a Open-Meteo una malla 5 × 5 sobre la caja del viaje en una consulta multi-ubicación y la predice con `POST /v2/predict/batch`. `RainGrid.at(lat, lon)` interpola bilinealmente. El costo de `dryest` es `travel_time × factor × (1 + 3 · p(punto medio))`; cada opción informa `rain_exposure`. El Backend pide `dryest` como alternativa.

## Technical Context

**Language/Version**: Python 3.11 (routing service), Java 21 (Backend, un parámetro).

**Primary Dependencies**: sin nuevas (numpy para la interpolación, ya presente vía OSMnx).

**Testing**: pytest con el grafo sintético de la spec 009 y grillas construidas a mano; `RoutingApiClientTest` para el parámetro nuevo.

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| IV. Contract-first | `contracts/routing-dryest.md`: campos aditivos (`rain_exposure`, `dryest_available`) y parámetro `alternative` del Backend. | ✅ |
| VI. Paridad train/serve | La grilla usa la misma fuente, variables, unidades y modelo; el ML API calcula las features. | ✅ |
| VII. Sin datos fabricados | Grilla incompleta → no disponible; no se rellena. | ✅ |
| Charter R-26 | Test con grilla no uniforme: `dryest` ≠ `fastest`. | ✅ |
| Charter R-27 | Factor de pendiente eliminado (spec 009); sin elevaciones, decisión documentada. | ✅ |

## Project Structure

```text
services/routing_api/
├── infrastructure/rain_signal.py           # + RainGrid, RainGridClient
├── infrastructure/networkx_routing_service.py  # costo dryest por arista, rain_exposure
├── application/dtos.py, use_cases.py       # campos nuevos
└── tests/test_dryest.py, tests/test_rain_grid.py
apps/backend/src/main/java/ti/mdva/service/routing/RoutingApiClient.java  # route_type alternativo
```

## Complexity Tracking

Sin violaciones.
