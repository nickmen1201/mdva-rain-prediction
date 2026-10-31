# Research: ruta `dryest` espacial

## R1. Por qué la versión anterior era ficticia (H-09)

El costo era `length × traffic × (1 + (penalty − 1) × 3)` con `penalty` calculado **una vez en el origen**: un escalar común a todas las aristas. Multiplicar todos los costos por la misma constante no cambia el argmin, así que `dryest` ≡ `fastest` salvo por empates. La alternativa "más seca" que veía el usuario era, en el mejor caso, la ruta más corta.

## R2. Grilla

- **Decision**: malla regular 5 × 5 sobre la caja origen–destino con 0.01° de margen y lado mínimo 0.02°; una petición multi-ubicación a Open-Meteo y una a `/v2/predict/batch` (25 registros, < 200 del límite).
- **Resolución efectiva**: la fuente del pronóstico tiene celdas de varios km; en viajes cortos varios puntos de la malla caen en la misma celda y la grilla es casi uniforme → `dryest` ≈ `fastest` (correcto). La ruta seca solo difiere cuando el viaje cruza celdas con pronósticos distintos.
- **Alternatives considered**: reutilizar la grilla de 81 puntos del heatmap del Backend (acopla el routing service al Backend); IDW (más costosa y sin ventaja sobre bilineal en una malla regular).

## R3. Costo

- **Decision**: `w = travel_time × factor_RF10 × (1 + 3 · p(punto medio))`. La sensibilidad 3.0 es la ya documentada; con p ∈ [0, 1] una arista con lluvia segura cuesta 4× su tiempo, lo que permite desvíos moderados sin rutas absurdas.
- **Exposición**: `Σ p · t / Σ t`, en la misma unidad que la probabilidad (comparable entre rutas).

## R4. Elevaciones (R-27)

- **Decision**: no se agregan. `ox.elevation.add_node_elevations_raster` requiere un DEM (SRTM, ~25 MB por tile) y `rasterio`; el único uso sería un factor de pendiente para bicicleta sin datos para calibrarlo. Se mantiene la eliminación del factor (spec 009) y se documenta.
