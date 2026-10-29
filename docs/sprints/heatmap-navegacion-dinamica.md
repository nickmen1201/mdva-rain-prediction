# MDVA - Heatmap de lluvia y navegacion dinamica

## Resumen

Implementacion del plan de heatmap de lluvia toggleable y navegacion dinamica para los mapas principales de MDVA.

- Fuente de lluvia: `POST /api/weather/predict-grid`, respaldado por Google Weather API + modelo ML.
- Render del heatmap: `deck.gl` sobre Google Maps para evitar depender de `google.maps.visualization.HeatmapLayer`.
- Pantallas afectadas: mapa post-login (`MapaCiudad`) y navegacion activa (`EnRuta`).
- Navegacion activa: boton `Centrar`, seguimiento de posicion, tilt y rotacion por heading GPS o heading calculado por movimiento.

## Sprints implementados

### Sprint 1 - Base reusable

- Se agregaron `WeatherHeatmapLayer`, `WeatherHeatmapToggle` y `CenterButton`.
- Se agregaron `useWeatherGrid` y `useNavigationCamera`.
- Se agregaron dependencias `deck.gl`, `@deck.gl/google-maps` y `@deck.gl/aggregation-layers`.

### Sprint 2 - Heatmap en mapa ciudad

- `MapaCiudad` ahora tiene toggle de lluvia persistido en `localStorage`.
- La grilla fija cubre Medellin con centro `{ lat: 6.2442, lng: -75.5812 }`.
- El heatmap se oculta y muestra un aviso si falla el endpoint.

### Sprint 3 - Heatmap en navegacion activa

- `EnRuta` usa la misma capa de lluvia.
- La grilla se centra en GPS si existe; de lo contrario usa el centro de la ruta.
- El hook evita recalculos cuando el toggle esta apagado y refresca cada 180 segundos.

### Sprint 4 - Centrar y seguimiento

- El marcador de usuario sigue rotando con heading GPS.
- Si el GPS no trae heading, se calcula con el vector entre la posicion anterior y la actual.
- La camara activa usa `panTo`, zoom 19, tilt 45 y heading suavizado.
- El usuario puede arrastrar el mapa para salir del seguimiento y usar `Centrar` para volver.

### Sprint 5 - Backend y rendimiento

- `WeatherController` delega la prediccion de grilla al servicio.
- `WeatherMLService` expone `predictGridForArea`.
- `WeatherMLServiceImpl` limita grillas a 81 puntos, cachea celdas por 180 segundos y responde `generatedAt`, `source` y `ttlSeconds`.

## Pruebas sugeridas

- Frontend: `npm run lint` y `npm run build`.
- Backend: `./gradlew test`.
- QA manual: activar/desactivar lluvia en ambos mapas, probar GPS permitido/denegado y arrastrar el mapa en navegacion para confirmar que `Centrar` reactiva el seguimiento.
