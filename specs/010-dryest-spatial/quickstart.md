# Quickstart: validar la ruta `dryest`

## 1. Tests

```bash
uv run --project services/routing_api pytest services/routing_api/tests/test_dryest.py services/routing_api/tests/test_rain_grid.py
```

Esperado: con una grilla no uniforme `dryest` ≠ `fastest` y su exposición a la lluvia es < 50 % de la de `fastest`; con grilla uniforme coinciden; una grilla incompleta o una señal no disponible no producen `dryest`.

## 2. Stack

```bash
make up
curl -s -X POST localhost:8000/api/v1/route -H 'Content-Type: application/json' \
  -d '{"origin":{"latitude":6.337,"longitude":-75.558},"destination":{"latitude":6.171,"longitude":-75.587}}' \
  | python -c "import json,sys; r=json.load(sys.stdin); print(r['dryest_available'], [(o['route_type'], o['rain_exposure']) for o in r['options']])"
```

Esperado: `dryest_available` según la lluvia del momento; cada opción con `rain_exposure`. Los logs del ML API muestran una sola llamada a `/v2/predict/batch` (25 registros) por viaje.

## Verificación registrada (2026-10-31)

Routing service y Backend construidos desde la instantánea exacta del commit:

- **SC-001** ✅ `test_dryest.py`: con grilla no uniforme `dryest` toma la calle seca (3 nodos) y `fastest` la avenida lluviosa; exposición de `dryest` < 50 % de la de `fastest`. 52 tests del routing service en verde.
- **SC-002** ✅ Bello (6.337, −75.558) → Envigado (6.171, −75.587): una sola llamada a `/v2/predict/batch` (25 registros) en los logs del ML API; la segunda consulta de la misma caja sale de caché.
- **SC-003** ✅ 2.3 s con el grafo cargado (12.7 s la primera, que carga el grafo).
- Con la lluvia del momento la grilla real varió entre 0.30 y 0.60, `dryest_available=true`, y `dryest` coincidió con `fastest` (exposición 0.37): la diferencia de lluvia entre caminos alternativos no compensó el desvío. Es el resultado correcto de la función de costo, documentado como limitación (spec Assumptions, research R2).
