# Research: Frontend sin Google

## R1. Hallazgos al leer el código actual

| ID | Hallazgo | Evidencia |
|---|---|---|
| H-35 | El heatmap multiplica la probabilidad hasta × 4.2 (`visualScale = 0.34 / maxWeight`) y le suma textura de ruido de valor ("nubes") con umbral local aleatorio: el color no corresponde a la probabilidad predicha | `WeatherHeatmapLayer.jsx::buildRainRaster` |
| H-36 | Un punto de la grilla sin probabilidad se pinta como 0 % (`probabilidadRf ?? 0`) y luego se suaviza con IDW de potencia 1.8 | `useWeatherGrid.js::normalizeResults`, `interpolateSurface` |
| H-37 | El botón de la alternativa siempre dice "ruta más seca" aunque la alternativa sea la más corta | `ResultadoViaje.jsx` |
| — | Google aparece en 8 archivos: proveedor `APIProvider`, `Map`, `useMap`, `useMapsLibrary('places'/'geocoding')`, `google.maps.{Marker,Polyline,LatLngBounds,geometry.encoding}`, `GoogleMapsOverlay` de deck.gl | `grep -rn google apps/frontend/src` |

## R2. Renderizador

- **Decision**: `maplibre-gl` directo (sin `react-map-gl`), envuelto en `MapView` con un contexto `useMap()` que imita la API usada por los componentes existentes.
- **Rationale**: una sola dependencia; los componentes ya estaban escritos como "efecto que dibuja sobre el mapa", así que solo cambian las primitivas.
- **Alternatives considered**: Leaflet (sin inclinación/rumbo nativos: rompería la navegación 3D); `react-map-gl` (otra capa más sin ventaja aquí).

## R3. Teselas

- **Decision**: raster OSM (`tile.openstreetmap.org`) con su atribución en ambos temas; el oscuro invierte el brillo (`raster-brightness-min` > `raster-brightness-max`) y rota el tono 180° en la misma capa. URL configurable (`VITE_TILES_URL`). Cambiar de tema solo cambia la pintura de la capa base, sin perder las capas dibujadas.
- **Descartado**: CARTO `dark_all`: al verificar con navegador sus teselas devolvieron la marca "API KEY REQUIRED" (constitución II: nada que exija key).

## R4. Heatmap

- **Decision**: interpolación bilineal sobre la malla 9 × 9 predicha (sin extrapolar fuera de ella), color por una escala fija con cortes en 0.40 y 0.70 (los umbrales de alerta) y opacidad creciente con la probabilidad; se publica como fuente `image` de MapLibre (canvas → data URL). Leyenda con la misma escala.
- **Alternatives considered**: `heatmap` nativo de MapLibre (densidad de puntos, no un campo continuo de probabilidad); deck.gl `BitmapLayer` (dos dependencias más para el mismo resultado).

## R5. Búsqueda de direcciones

- **Decision**: `PlaceSearch` (campo + botón/Enter → `GET /api/geocoding/search`, hasta 5 resultados); tocar el mapa fija el primer punto que falte y los pines son arrastrables, ambos con `GET /api/geocoding/reverse`.
