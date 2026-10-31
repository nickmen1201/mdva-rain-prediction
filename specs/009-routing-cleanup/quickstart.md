# Quickstart: validar la limpieza del routing service

## 1. Tests (sin red ni grafo OSM)

```bash
uv run --project services/routing_api pytest services/routing_api/tests
uv run --project services/ml_api pytest services/ml_api/tests
```

Esperado: señal de lluvia (`test_rain_signal.py`), nodo más cercano, costos por arista (`test_routing_weights.py`), pasos (`test_navigation.py`), CORS (`test_app.py`) y `/route/spring` en verde; en el ML API, `/predecir/*` y `/monitorear/trayecto` → 404.

## 2. Sin artefactos heredados

```bash
git ls-files | grep -E "rain_model|random_forest.pkl|regresion_logistica.pkl|train_rain_model"   # sin resultados
grep -n scikit-learn services/routing_api/pyproject.toml                                         # sin resultados
```

## 3. Stack

```bash
make up && make smoke
```

Esperado: `routing_route` 200; la primera ruta tras el arranque agrega velocidades y tiempos al grafo en caché (una sola vez); `viajes_planificar` 201 con una duración realista.

## Verificación registrada (2026-10-31)

Stack construido desde la instantánea exacta del commit (índice de git), sin API keys:

- **SC-001** ✅ `git ls-files` sin `rain_model*`, `train_rain_model.py`, `random_forest.pkl` ni `regresion_logistica.pkl` (−67 MB y −4.6 MB).
- **SC-002** ✅ 41 tests del routing service (grafo sintético de 5 nodos, sin red) y 36 del ML API.
- **SC-003** ✅ smoke test completo en verde: `routing_route` 200 con `clima_disponible=true`; Parque Berrío → El Poblado `fastest` 6.26 km en **8.4 min** (velocidades por vía de OSM; antes, siempre distancia / 40 km/h); `viajes_planificar` 201; `ml_v1_retirado` 404. El grafo cacheado se completó con tiempos y se guardó una vez (`Guardando grafo con velocidades y tiempos en caché`).
- **SC-004** ✅ `scikit-learn` fuera de `services/routing_api/pyproject.toml` y de su `uv.lock`.
